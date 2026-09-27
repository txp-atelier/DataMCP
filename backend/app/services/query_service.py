import re


class QueryService:

    BLOCKED_KEYWORDS = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
    }

    def validate_read_query(self, query: str) -> None:
        query = query.strip()

        if not query:
            raise ValueError("Query cannot be empty")

        # ---------------------------------------------------------
        # 1. Reject SQL comments
        # ---------------------------------------------------------
        #
        # Comments are not needed for Agent-generated read queries
        # and can make query validation harder to reason about.
        #

        if "--" in query:
            raise ValueError(
                "SQL comments are not allowed"
            )

        if "/*" in query or "*/" in query:
            raise ValueError(
                "SQL block comments are not allowed"
            )

        # ---------------------------------------------------------
        # 2. Reject multiple SQL statements
        # ---------------------------------------------------------
        #
        # A single read-only statement is expected.
        #

        statements = [
            statement.strip()
            for statement in query.split(";")
            if statement.strip()
        ]

        if len(statements) != 1:
            raise ValueError(
                "Only one SQL statement is allowed"
            )

        query = statements[0]

        # ---------------------------------------------------------
        # 3. Allow SELECT or WITH queries
        # ---------------------------------------------------------

        normalized_query = re.sub(
            r"\s+",
            " ",
            query.upper(),
        ).strip()

        if not (
            normalized_query.startswith("SELECT ")
            or normalized_query.startswith("SELECT")
            or normalized_query.startswith("WITH ")
            or normalized_query.startswith("WITH")
        ):
            raise ValueError(
                "Only read-only SELECT or WITH queries are allowed"
            )

        # ---------------------------------------------------------
        # 4. Block destructive SQL keywords
        # ---------------------------------------------------------

        for keyword in self.BLOCKED_KEYWORDS:
            if re.search(
                rf"\b{keyword}\b",
                normalized_query,
            ):
                raise ValueError(
                    f"Query contains blocked keyword: {keyword}"
                )


query_service = QueryService()
