from __future__ import annotations

import ast
import operator
import re
from typing import Any


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_NUMBER_SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "million": 1_000_000,
}

_FILLER_WORDS = {
    "a",
    "an",
    "by",
    "calculate",
    "can",
    "could",
    "compute",
    "evaluate",
    "for",
    "is",
    "me",
    "please",
    "result",
    "s",
    "tell",
    "the",
    "what",
    "whats",
    "you",
}

_NUMBER_TOKEN_PATTERN = re.compile(r"^\d+(\.\d+)?$")


def _normalize_expression(raw_expression: str) -> str:
    normalized = raw_expression.lower().strip()
    if not normalized:
        return ""

    replacements = [
        ("raised to the power of", " ** "),
        ("to the power of", " ** "),
        ("power of", " ** "),
        ("multiplied by", " * "),
        ("times", " * "),
        ("divided by", " / "),
        ("over", " / "),
        ("plus", " + "),
        ("minus", " - "),
        ("modulo", " % "),
        ("mod", " % "),
        ("open parenthesis", " ( "),
        ("close parenthesis", " ) "),
        ("left parenthesis", " ( "),
        ("right parenthesis", " ) "),
    ]

    for source, target in replacements:
        normalized = normalized.replace(source, target)

    normalized = normalized.replace("?", " ").replace(",", " ")
    tokens = re.findall(r"\d+\.\d+|\d+|\*\*|[()+\-*/%]|[a-z]+", normalized)

    expression_tokens: list[str] = []
    word_buffer: list[str] = []

    def flush_word_buffer() -> None:
        if not word_buffer:
            return

        cleaned_tokens = [token for token in word_buffer if token not in _FILLER_WORDS]
        numeric_value = _number_words_to_string(cleaned_tokens)
        if numeric_value is not None:
            expression_tokens.append(numeric_value)
        else:
            expression_tokens.extend(cleaned_tokens)
        word_buffer.clear()

    for token in tokens:
        if token == "x":
            flush_word_buffer()
            expression_tokens.append("*")
            continue

        if _NUMBER_TOKEN_PATTERN.match(token) or token in {"**", "+", "-", "*", "/", "%", "(", ")"}:
            flush_word_buffer()
            expression_tokens.append(token)
            continue

        word_buffer.append(token)

    flush_word_buffer()

    expression = " ".join(expression_tokens)
    expression = re.sub(r"\s+", " ", expression).strip()
    if not expression or re.search(r"[a-z]", expression):
        return ""
    if not re.search(r"\d", expression):
        return ""

    return expression


def _number_words_to_string(tokens: list[str]) -> str | None:
    if not tokens:
        return None

    filtered = [token for token in tokens if token != "and"]
    if not filtered:
        return None

    if any(token == "point" for token in filtered):
        split_index = filtered.index("point")
        integer_part = _number_words_to_int(filtered[:split_index])
        decimal_digits = []
        for token in filtered[split_index + 1 :]:
            if token not in _NUMBER_WORDS or _NUMBER_WORDS[token] >= 10:
                return None
            decimal_digits.append(str(_NUMBER_WORDS[token]))

        if integer_part is None or not decimal_digits:
            return None
        return f"{integer_part}.{''.join(decimal_digits)}"

    integer_value = _number_words_to_int(filtered)
    if integer_value is None:
        return None
    return str(integer_value)


def _number_words_to_int(tokens: list[str]) -> int | None:
    if not tokens:
        return None

    total = 0
    current = 0

    for token in tokens:
        if token in _NUMBER_WORDS:
            current += _NUMBER_WORDS[token]
            continue

        if token == "hundred":
            current = max(current, 1) * 100
            continue

        if token in {"thousand", "million"}:
            scale = _NUMBER_SCALES[token]
            current = max(current, 1)
            total += current * scale
            current = 0
            continue

        return None

    return total + current


def _evaluate_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand))

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)

        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("division by zero")
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("Exponent is too large for this demo calculator.")

        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if abs(result) > 1_000_000_000:
            raise ValueError("Result is too large for this demo calculator.")
        return result

    raise ValueError("Unsupported expression.")


def _format_result(value: float) -> str:
    if value.is_integer():
        return str(int(value))

    return f"{value:.10f}".rstrip("0").rstrip(".")


async def calculate_expression(arguments: dict[str, Any]) -> str:
    raw_expression = str(arguments.get("expression") or "").strip()
    expression = _normalize_expression(raw_expression)

    if not expression:
        return "I could not find a valid arithmetic expression to calculate."

    try:
        parsed = ast.parse(expression, mode="eval")
        result = _evaluate_node(parsed)
    except ZeroDivisionError:
        return "That expression tries to divide by zero, so it cannot be evaluated."
    except Exception:
        return "I could not safely evaluate that expression. Try a simpler arithmetic request."

    formatted_result = _format_result(result)
    return f"The result of {expression} is {formatted_result}."
