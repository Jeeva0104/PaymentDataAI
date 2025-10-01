import re
import logging
from typing import Tuple, List, Optional, Dict

logger = logging.getLogger(__name__)

# SQL Keywords that should never be treated as table names
SQL_KEYWORDS = {
    # PostgreSQL-specific advanced features
    'lateral', 'tablesample', 'unnest', 'recursive', 'materialized',
    
    # Common SQL keywords that could appear after JOIN/FROM
    'values', 'generate_series', 'information_schema', 'pg_catalog',
    
    # Subquery and CTE keywords
    'with', 'ordinality',
    
    # Window function keywords
    'over', 'partition', 'rows', 'range', 'preceding', 'following', 
    'unbounded', 'current', 'row',
    
    # Logical operators and conditions
    'not', 'exists', 'in', 'any', 'all', 'some', 'between',
    
    # Data type and casting keywords
    'cast', 'convert', 'array', 'row', 'record',
    
    # Function keywords
    'case', 'when', 'then', 'else', 'end', 'coalesce', 'nullif',
    
    # JSON/JSONB functions (PostgreSQL)
    'jsonb_array_elements', 'jsonb_object_keys', 'json_each', 'jsonb_each',
    
    # Set operations
    'union', 'intersect', 'except',
    
    # Other potentially problematic keywords
    'default', 'null', 'true', 'false'
}


def extract_lateral_subqueries(query_part: str) -> List[Tuple[str, str]]:
    """
    Extract LATERAL subqueries from a query part
    Returns list of (context, subquery) tuples
    """
    # Find LATERAL constructs with balanced parentheses
    lateral_pattern = r"\b(?:inner\s+join|left\s+join|right\s+join|full\s+outer\s+join|cross\s+join)\s+lateral\s*\("
    
    lateral_subqueries = []
    pos = 0
    
    while pos < len(query_part):
        match = re.search(lateral_pattern, query_part[pos:], re.IGNORECASE)
        if not match:
            break
            
        # Find the opening parenthesis position
        start_pos = pos + match.end() - 1  # Position of opening parenthesis
        
        # Find matching closing parenthesis
        paren_count = 0
        subquery_start = start_pos + 1
        subquery_end = start_pos
        
        for i in range(start_pos, len(query_part)):
            char = query_part[i]
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    subquery_end = i
                    break
        
        if paren_count == 0:
            # Extract the subquery content
            subquery = query_part[subquery_start:subquery_end].strip()
            lateral_subqueries.append((f"LATERAL subquery", subquery))
        
        pos = subquery_end + 1
    
    return lateral_subqueries


def filter_sql_keywords(tables: List[str]) -> List[str]:
    """
    Filter out SQL keywords from table list
    Returns list of actual table names
    """
    return [
        table for table in tables 
        if table.lower() not in SQL_KEYWORDS
    ]


def extract_tables_from_query(
    query_part: str, cte_names: List[str] = None
) -> List[str]:
    """
    Extract all table names from a query part (CTE or main query)
    Handles: FROM table, JOIN table, table aliases, schema prefixes
    Excludes CTE names and SQL keywords from being treated as tables
    """
    if cte_names is None:
        cte_names = []

    # Create keyword exclusion pattern
    keyword_exclusion = "|".join(SQL_KEYWORDS)
    
    patterns = [
        # Standard FROM/JOIN with keyword exclusion and optional alias and schema prefix
        rf"\b(?:from|join)\s+(?!(?:{keyword_exclusion})\b)(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]+)(?:\s+(?:as\s+)?[a-zA-Z_][a-zA-Z0-9_]*)?",
        # Different JOIN types with keyword exclusion
        rf"\b(?:inner\s+join|left\s+join|right\s+join|full\s+outer\s+join|cross\s+join)\s+(?!(?:{keyword_exclusion})\b)(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]+)",
    ]

    tables = []
    for pattern in patterns:
        matches = re.findall(pattern, query_part, re.IGNORECASE | re.DOTALL)
        tables.extend(matches)

    # Extract tables from LATERAL subqueries
    lateral_subqueries = extract_lateral_subqueries(query_part)
    for context, subquery in lateral_subqueries:
        lateral_tables = extract_tables_from_query(subquery, cte_names)
        tables.extend(lateral_tables)

    # Remove duplicates and filter out CTE names and SQL keywords
    unique_tables = list(set(tables))
    filtered_tables = [
        table
        for table in unique_tables
        if table.lower() not in [cte.lower() for cte in cte_names]
    ]
    
    # Additional keyword filtering as safety net
    filtered_tables = filter_sql_keywords(filtered_tables)

    return filtered_tables


def extract_subqueries(query_part: str) -> List[Tuple[str, str]]:
    """
    Extract all subqueries from a query part
    Returns list of (context, subquery) tuples
    """
    # Find all SELECT statements within parentheses
    subquery_pattern = r"\(\s*(select\s+.*?)\s*\)"
    subqueries = re.findall(subquery_pattern, query_part, re.IGNORECASE | re.DOTALL)

    numbered_subqueries = []
    for i, subquery in enumerate(subqueries, 1):
        numbered_subqueries.append((f"Subquery {i}", subquery))

    return numbered_subqueries


def parse_cte_query(query: str) -> Tuple[bool, List[Tuple[str, str]], str]:
    """
    Parse CTE query into individual CTEs and main query
    Returns: (is_valid, [(cte_name, cte_query), ...], main_query)
    """
    # First, find all WITH...AS(...) patterns to identify CTE boundaries
    with_pattern = r"^\s*with\s+"
    if not re.match(with_pattern, query, re.IGNORECASE):
        return False, [], ""

    # Remove the WITH keyword and find the main SELECT
    query_without_with = re.sub(with_pattern, "", query, flags=re.IGNORECASE).strip()
    
    # Skip RECURSIVE and MATERIALIZED keywords if present
    query_without_with = re.sub(r"^\s*recursive\s+", "", query_without_with, flags=re.IGNORECASE).strip()
    query_without_with = re.sub(r"^\s*materialized\s+", "", query_without_with, flags=re.IGNORECASE).strip()

    # Parse CTEs by finding balanced parentheses
    ctes = []
    pos = 0

    while pos < len(query_without_with):
        # Skip whitespace
        while pos < len(query_without_with) and query_without_with[pos].isspace():
            pos += 1

        if pos >= len(query_without_with):
            break

        # Check if we've reached the main SELECT
        remaining = query_without_with[pos:]
        if re.match(r"^\s*select\s+", remaining, re.IGNORECASE):
            # Found main SELECT, extract it
            main_query = remaining.strip()
            return True, ctes, main_query

        # Try to match CTE name (handle MATERIALIZED keyword before CTE name)
        name_match = re.match(
            r"^(?:materialized\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", remaining, re.IGNORECASE
        )
        if not name_match:
            # If we can't match a CTE pattern and haven't found SELECT, it's invalid
            return False, [], ""

        cte_name = name_match.group(1)
        pos += name_match.end() - 1  # Position at opening parenthesis

        # Find matching closing parenthesis
        paren_count = 0
        cte_start = pos + 1  # Start after opening parenthesis
        cte_end = pos

        for i in range(pos, len(query_without_with)):
            char = query_without_with[i]
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
                if paren_count == 0:
                    cte_end = i
                    break

        if paren_count != 0:
            return False, [], ""

        # Extract CTE query content
        cte_query = query_without_with[cte_start:cte_end].strip()
        ctes.append((cte_name, cte_query))

        # Move past the closing parenthesis
        pos = cte_end + 1

        # Skip whitespace and optional comma
        while pos < len(query_without_with) and query_without_with[pos].isspace():
            pos += 1

        if pos < len(query_without_with) and query_without_with[pos] == ",":
            pos += 1  # Skip comma

    # If we get here without finding a main SELECT, it's invalid
    return False, [], ""


def validate_security_patterns(
    query_part: str, context: str
) -> Tuple[bool, Optional[str]]:
    """
    Apply security validations to a query part
    """
    # Check for multiple semicolons
    semicolon_count = query_part.count(";")
    if semicolon_count > 1:
        return False, f"{context}: Multiple semicolons not allowed"

    # Check for UNION clauses
    if re.search(r"\bunion\b", query_part, re.IGNORECASE):
        return False, f"{context}: UNION clauses not allowed"

    # Check for OR injection patterns
    if re.search(
        r'\bor\s*(?:/\*.*?\*/)?\s*[\'"]?1[\'"]?\s*=\s*[\'"]?1[\'"]?',
        query_part,
        re.IGNORECASE,
    ):
        return False, f"{context}: Suspicious OR condition detected"

    # Check for OR with quoted strings
    if re.search(
        r'\bor\s*(?:/\*.*?\*/)?\s*[\'"][^\'"]*[\'"]\s*=\s*[\'"][^\'"]*[\'"]',
        query_part,
        re.IGNORECASE,
    ):
        return False, f"{context}: Suspicious OR condition with quoted strings"

    return True, None


def find_id_equality_values_in_query_part(query_part: str, id_name: str) -> List[str]:
    """
    Find ALL equality values for a specific ID field in any query part
    Returns list of ID values found in equality conditions
    
    Args:
        query_part: SQL query part to search
        id_name: Name of the ID field (e.g., 'merchant_id', 'profile_id', 'organisation_id')
    
    Returns:
        List of ID values found in equality conditions
    """
    patterns = [
        rf"\b{id_name}\s*=\s*'([^']*)'",  # Single quotes
        rf'\b{id_name}\s*=\s*"([^"]*)"',  # Double quotes
        rf"\b\w+\.{id_name}\s*=\s*'([^']*)'",  # With table alias
        rf'\b\w+\.{id_name}\s*=\s*"([^"]*)"',  # With table alias + double quotes
    ]

    found_ids = []
    for pattern in patterns:
        matches = re.findall(pattern, query_part, re.IGNORECASE)
        found_ids.extend(matches)

    return found_ids


def find_id_conditions_in_where_clause(query_part: str, id_name: str) -> List[str]:
    """
    Find ALL conditions for a specific ID field specifically in WHERE clauses
    Returns list of all condition types found in WHERE clauses only
    
    Args:
        query_part: SQL query part to search
        id_name: Name of the ID field (e.g., 'merchant_id', 'profile_id', 'organisation_id')
    
    Returns:
        List of all condition patterns found for the specified ID in WHERE clauses
    """
    # Extract WHERE clause content - match until GROUP BY, ORDER BY, HAVING, LIMIT, or end of string
    where_match = re.search(
        r"\bwhere\s+(.*?)(?:\s+(?:group\s+by|order\s+by|having|limit)\b|$)",
        query_part,
        re.IGNORECASE | re.DOTALL,
    )
    if not where_match:
        return []

    where_clause = where_match.group(1).strip()

    # Patterns to detect any ID usage in WHERE clause
    # Note: These patterns are designed to match the actual conditions, not just find ID text
    # Patterns are ordered to avoid overlaps - more specific patterns first
    patterns = [
        rf"\b\w+\.{id_name}\s*=\s*['\"][^'\"]*['\"]",  # With table alias equality (specific first)
        rf"\b\w+\.{id_name}\s*(?:!=|<>)\s*['\"][^'\"]*['\"]",  # With alias inequality
        rf"\b\w+\.{id_name}\s*(?:>|<|>=|<=)\s*['\"][^'\"]*['\"]",  # With alias comparison
        rf"\b\w+\.{id_name}\s+(?:like|ilike)\s+['\"][^'\"]*['\"]",  # With alias LIKE
        rf"\b\w+\.{id_name}\s+(?:not\s+)?in\s*\([^)]*\)",  # With alias IN (complete)
        rf"\b\w+\.{id_name}\s+(?:not\s+)?between\s+['\"][^'\"]*['\"]",  # With alias BETWEEN
        rf"\b\w+\.{id_name}\s*(?:is\s+(?:not\s+)?null)",  # With alias NULL checks
        rf"\b{id_name}\s*=\s*['\"][^'\"]*['\"]",  # Equality (without alias)
        rf"\b{id_name}\s*(?:!=|<>)\s*['\"][^'\"]*['\"]",  # Inequality
        rf"\b{id_name}\s*(?:>|<|>=|<=)\s*['\"][^'\"]*['\"]",  # Comparison
        rf"\b{id_name}\s+(?:like|ilike)\s+['\"][^'\"]*['\"]",  # LIKE/ILIKE
        rf"\b{id_name}\s+(?:not\s+)?in\s*\([^)]*\)",  # IN/NOT IN (complete)
        rf"\b{id_name}\s+(?:not\s+)?between\s+['\"][^'\"]*['\"]",  # BETWEEN (start)
        rf"\b{id_name}\s*(?:is\s+(?:not\s+)?null)",  # IS NULL/IS NOT NULL
        rf"\b\w+\s*\(\s*(?:\w+\.)?{id_name}\s*\)",  # Function calls on ID
    ]

    found_references = []
    for pattern in patterns:
        matches = re.findall(pattern, where_clause, re.IGNORECASE)
        found_references.extend(matches)

    return found_references


def find_multiple_id_conditions_in_where_clause(query_part: str, id_names: List[str]) -> Dict[str, List[str]]:
    """
    Find ALL conditions for multiple ID fields specifically in WHERE clauses
    Returns dict with lists of condition types found for each ID type
    
    Args:
        query_part: SQL query part to search
        id_names: List of ID field names (e.g., ['profile_id', 'merchant_id', 'organisation_id'])
    
    Returns:
        Dictionary mapping each ID name to list of conditions found in WHERE clause
    """
    results = {}
    for id_name in id_names:
        results[id_name] = find_id_conditions_in_where_clause(query_part, id_name)
    return results
