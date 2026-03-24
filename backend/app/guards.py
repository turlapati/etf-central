"""
Guard Expression Parser and Evaluator

Provides safe evaluation of guard expressions for state machine transitions.
Supports tiered complexity:
- MVP: Simple context/payload field comparisons
- MVP+: Compound AND/OR conditions
- MVP++: JSON Logic (future)

Guard expressions are evaluated against context and payload data to determine
if a transition should be allowed.
"""
import re
import operator
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GuardResult:
    """Result of guard evaluation."""
    passed: bool
    reason: str = ""
    failed_expression: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"passed": self.passed, "reason": self.reason}
        if self.failed_expression:
            result["failed_expression"] = self.failed_expression
        return result


class GuardExpressionError(Exception):
    """Raised when a guard expression is invalid."""
    pass


class SafeGuardEvaluator:
    """
    Safely evaluates guard expressions without using Python's eval().
    
    Supported operators:
    - Comparison: ==, !=, <, <=, >, >=
    - Logical: and, or, not
    - Membership: in, not in
    - Null checks: is None, is not None
    
    Supported value access:
    - context.field_name
    - payload.field_name
    - Nested: context.user.name
    - Literals: numbers, strings, booleans, None
    """
    
    COMPARISON_OPS = {
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
    }
    
    COMPARISON_PATTERN = re.compile(
        r"^(.+?)\s*(==|!=|<=|>=|<|>)\s*(.+)$"
    )
    
    MEMBERSHIP_PATTERN = re.compile(
        r"^(.+?)\s+(not\s+in|in)\s+(.+)$"
    )
    
    NULL_CHECK_PATTERN = re.compile(
        r"^(.+?)\s+(is\s+not|is)\s+(None|null)$",
        re.IGNORECASE
    )
    
    def __init__(self, context: Dict[str, Any], payload: Dict[str, Any]):
        self.context = context
        self.payload = payload
    
    def evaluate(self, expression: str) -> bool:
        """
        Evaluate a single guard expression.
        
        Args:
            expression: Guard expression string
            
        Returns:
            True if guard passes, False otherwise
            
        Raises:
            GuardExpressionError: If expression is invalid
        """
        expression = expression.strip()
        
        if not expression:
            return True
        
        # Handle compound expressions with 'and'/'or'
        if " and " in expression:
            parts = self._split_logical(expression, " and ")
            return all(self.evaluate(p) for p in parts)
        
        if " or " in expression:
            parts = self._split_logical(expression, " or ")
            return any(self.evaluate(p) for p in parts)
        
        # Handle 'not' prefix
        if expression.startswith("not "):
            return not self.evaluate(expression[4:])
        
        # Try null check first
        null_match = self.NULL_CHECK_PATTERN.match(expression)
        if null_match:
            return self._evaluate_null_check(null_match)
        
        # Try membership check
        membership_match = self.MEMBERSHIP_PATTERN.match(expression)
        if membership_match:
            return self._evaluate_membership(membership_match)
        
        # Try comparison
        comparison_match = self.COMPARISON_PATTERN.match(expression)
        if comparison_match:
            return self._evaluate_comparison(comparison_match)
        
        # If no pattern matches, try to evaluate as boolean value
        try:
            value = self._resolve_value(expression)
            return bool(value)
        except Exception as e:
            raise GuardExpressionError(f"Invalid expression: {expression} - {e}")
    
    def _split_logical(self, expression: str, separator: str) -> List[str]:
        """Split expression by logical operator, respecting parentheses."""
        parts = []
        depth = 0
        current = []
        
        tokens = expression.split()
        sep_tokens = separator.strip().split()
        sep_len = len(sep_tokens)
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            if token == "(":
                depth += 1
            elif token == ")":
                depth -= 1
            
            if depth == 0 and i + sep_len <= len(tokens):
                if tokens[i:i+sep_len] == sep_tokens:
                    if current:
                        parts.append(" ".join(current))
                        current = []
                    i += sep_len
                    continue
            
            current.append(token)
            i += 1
        
        if current:
            parts.append(" ".join(current))
        
        return parts
    
    def _evaluate_comparison(self, match: re.Match) -> bool:
        """Evaluate a comparison expression."""
        left_expr, op, right_expr = match.groups()
        
        left_value = self._resolve_value(left_expr.strip())
        right_value = self._resolve_value(right_expr.strip())
        
        op_func = self.COMPARISON_OPS.get(op)
        if not op_func:
            raise GuardExpressionError(f"Unknown operator: {op}")
        
        try:
            return op_func(left_value, right_value)
        except TypeError as e:
            raise GuardExpressionError(f"Cannot compare {left_expr} {op} {right_expr}: {e}")
    
    def _evaluate_membership(self, match: re.Match) -> bool:
        """Evaluate a membership expression (in/not in)."""
        item_expr, op, container_expr = match.groups()
        
        item = self._resolve_value(item_expr.strip())
        container = self._resolve_value(container_expr.strip())
        
        try:
            result = item in container
            if "not" in op:
                return not result
            return result
        except TypeError as e:
            raise GuardExpressionError(f"Cannot check membership: {e}")
    
    def _evaluate_null_check(self, match: re.Match) -> bool:
        """Evaluate a null check expression."""
        value_expr, op, _ = match.groups()
        
        value = self._resolve_value(value_expr.strip())
        
        is_none = value is None
        if "not" in op:
            return not is_none
        return is_none
    
    def _resolve_value(self, expr: str) -> Any:
        """
        Resolve an expression to its value.
        
        Handles:
        - context.field, payload.field
        - Nested access: context.user.name
        - Literals: numbers, strings, booleans, None, lists
        """
        expr = expr.strip()
        
        # None/null
        if expr.lower() in ("none", "null"):
            return None
        
        # Boolean
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False
        
        # String literal (quoted)
        if (expr.startswith('"') and expr.endswith('"')) or \
           (expr.startswith("'") and expr.endswith("'")):
            return expr[1:-1]
        
        # List literal
        if expr.startswith("[") and expr.endswith("]"):
            inner = expr[1:-1].strip()
            if not inner:
                return []
            items = [self._resolve_value(item.strip()) for item in inner.split(",")]
            return items
        
        # Number
        try:
            if "." in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        
        # Context/payload access
        if expr.startswith("context."):
            return self._get_nested_value(self.context, expr[8:])
        if expr.startswith("payload."):
            return self._get_nested_value(self.payload, expr[8:])
        
        # Bare field name - try context first, then payload
        if "." not in expr and not expr.startswith(("context", "payload")):
            if expr in self.context:
                return self.context[expr]
            if expr in self.payload:
                return self.payload[expr]
        
        raise GuardExpressionError(f"Cannot resolve value: {expr}")
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a nested value from a dict using dot notation."""
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                if part not in current:
                    return None
                current = current[part]
            else:
                return None
        
        return current


def evaluate_guards(
    guard_expression: str,
    context: Dict[str, Any],
    payload: Dict[str, Any]
) -> GuardResult:
    """
    Evaluate guard expressions against context and payload.
    
    Args:
        guard_expression: Guard expression(s), newline or semicolon separated
        context: Instance context data
        payload: Trigger payload data
        
    Returns:
        GuardResult with passed status and reason if failed
    """
    if not guard_expression or not guard_expression.strip():
        return GuardResult(passed=True)
    
    evaluator = SafeGuardEvaluator(context, payload)
    
    # Parse multiple guards (newline or semicolon separated)
    guards = []
    for line in guard_expression.replace(";", "\n").split("\n"):
        line = line.strip()
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue
        # Remove leading dash (list item marker)
        if line.startswith("-"):
            line = line[1:].strip()
        if line:
            guards.append(line)
    
    # Evaluate each guard
    for guard in guards:
        try:
            result = evaluator.evaluate(guard)
            if not result:
                return GuardResult(
                    passed=False,
                    reason=f"Guard condition not met: {guard}",
                    failed_expression=guard
                )
        except GuardExpressionError as e:
            return GuardResult(
                passed=False,
                reason=str(e),
                failed_expression=guard
            )
        except Exception as e:
            logger.error(f"Unexpected error evaluating guard '{guard}': {e}")
            return GuardResult(
                passed=False,
                reason=f"Guard evaluation error: {e}",
                failed_expression=guard
            )
    
    return GuardResult(passed=True)
