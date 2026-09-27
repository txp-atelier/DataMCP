import json
import os
import re

from groq import Groq

from app.services.mcp_client_service import mcp_client_service


class AgentService:

    MODEL = "openai/gpt-oss-120b"
    MAX_TOOL_ITERATIONS = 5

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set"
            )

        self.client = Groq(api_key=api_key)

    async def _get_tools(self) -> list[dict]:
        mcp_tools = await mcp_client_service.list_tools()

        tools = []

        for tool in mcp_tools:
            input_schema = tool["input_schema"].copy()

            properties = input_schema.get(
                "properties",
                {},
            ).copy()

            required = input_schema.get(
                "required",
                [],
            ).copy()

            # user_id is controlled by the application.
            # It must not be requested from the LLM.
            properties.pop("user_id", None)

            required = [
                field
                for field in required
                if field != "user_id"
            ]

            input_schema["properties"] = properties

            if required:
                input_schema["required"] = required
            else:
                input_schema.pop("required", None)

            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": input_schema,
                    },
                }
            )

        return tools

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        user_id: str,
    ):
        return await mcp_client_service.call_tool(
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
        )

    @staticmethod
    def _serialize_tool_result(result) -> str:
        """
        Convert an MCP result into a JSON/text string that can safely
        be passed back to the LLM.
        """

        # MCP structured content
        if hasattr(result, "structuredContent"):
            structured_content = result.structuredContent

            if structured_content:
                if "result" in structured_content:
                    return json.dumps(
                        structured_content["result"],
                        default=str,
                    )

                return json.dumps(
                    structured_content,
                    default=str,
                )

        # MCP text content
        if hasattr(result, "content"):
            content = result.content

            if isinstance(content, list):
                parts = []

                for item in content:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    else:
                        parts.append(str(item))

                if len(parts) == 1:
                    return parts[0]

                parsed_parts = []

                for part in parts:
                    try:
                        parsed_parts.append(json.loads(part))
                    except json.JSONDecodeError:
                        parsed_parts = []
                        break

                if parsed_parts:
                    return json.dumps(
                        parsed_parts,
                        default=str,
                    )

                return "\n".join(parts)

        return str(result)

    async def _resolve_database(
        self,
        question: str,
        user_id: str,
        connection_id: str | None = None,
    ) -> dict | None:
        """
        Deterministically resolve a database.

        Resolution priority:

        1. Explicit database name/type in the question.
        2. Selected/default database.
        3. Table-based database resolution.
        4. Ambiguous result when multiple databases match.

        Returns:

            {
                "status": "resolved",
                "connection_id": "...",
                "connection_name": "..."
            }

        Or:

            {
                "status": "ambiguous",
                "message": "..."
            }

        Or None when the question is not clearly database-specific.
        """

        connections_result = await self._execute_tool(
            tool_name="list_connections",
            arguments={},
            user_id=user_id,
        )

        connections_text = self._serialize_tool_result(
            connections_result
        )

        try:
            connections = json.loads(connections_text)
        except json.JSONDecodeError:
            return None

        if not connections:
            return {
                "status": "ambiguous",
                "message": "No databases are currently connected to DataMCP.",
            }

        question_lower = question.lower()

        # ---------------------------------------------------------
        # 1. Explicit database-name selection
        # ---------------------------------------------------------

        explicit_matches = []

        for connection in connections:
            name = connection.get("name", "")
            database_type = connection.get("database_type", "")

            identifiers = {
                name.lower(),
                database_type.lower(),
            }

            for identifier in identifiers:
                if identifier and identifier in question_lower:
                    explicit_matches.append(connection)
                    break

        if len(explicit_matches) == 1:
            connection = explicit_matches[0]

            return {
                "status": "resolved",
                "connection_id": connection["id"],
                "connection_name": connection["name"],
            }

        if len(explicit_matches) > 1:
            names = [
                connection["name"]
                for connection in explicit_matches
            ]

            return {
                "status": "ambiguous",
                "message": (
                    "The question mentions multiple databases: "
                    + ", ".join(names)
                    + ". Please specify which database to use."
                ),
            }

        # ---------------------------------------------------------
        # 2. Selected/default database
        # ---------------------------------------------------------

        if connection_id:
            selected_connection = next(
                (
                    connection
                    for connection in connections
                    if connection.get("id") == connection_id
                ),
                None,
            )

            if selected_connection is None:
                return {
                    "status": "ambiguous",
                    "message": "The selected database is no longer available.",
                }

            return {
                "status": "resolved",
                "connection_id": selected_connection["id"],
                "connection_name": selected_connection["name"],
            }

        # ---------------------------------------------------------
        # 3. Find tables mentioned in the question
        # ---------------------------------------------------------

        database_table_matches = []

        for connection in connections:
            try:
                schema_result = await self._execute_tool(
                    tool_name="get_database_schema",
                    arguments={
                        "connection_id": connection["id"],
                    },
                    user_id=user_id,
                )

                schema_text = self._serialize_tool_result(
                    schema_result
                )

                schema_data = json.loads(schema_text)

                tables = schema_data.get("schema", {}).get(
                    "tables",
                    {},
                )

                for table_name in tables:
                    if table_name.lower() in question_lower:
                        database_table_matches.append(
                            {
                                "connection": connection,
                                "table": table_name,
                            }
                        )

            except Exception:
                continue

        # ---------------------------------------------------------
        # 4. Exactly one database contains the mentioned table
        # ---------------------------------------------------------

        matched_connections = {}

        for match in database_table_matches:
            connection = match["connection"]
            matched_connections[connection["id"]] = connection

        if len(matched_connections) == 1:
            connection = next(
                iter(matched_connections.values())
            )

            return {
                "status": "resolved",
                "connection_id": connection["id"],
                "connection_name": connection["name"],
            }

        # ---------------------------------------------------------
        # 5. Multiple databases contain the mentioned table
        # ---------------------------------------------------------

        if len(matched_connections) > 1:
            names = [
                connection["name"]
                for connection in matched_connections.values()
            ]

            tables = sorted(
                {
                    match["table"]
                    for match in database_table_matches
                }
            )

            return {
                "status": "ambiguous",
                "message": (
                    f"The table `{', '.join(tables)}` exists in "
                    f"multiple connected databases: "
                    f"{', '.join(names)}. "
                    "Please specify which database you want to use."
                ),
            }

        return None

    @staticmethod
    def _validate_tool_call(
        tool_name: str,
        arguments: dict,
        available_tool_names: set[str],
        resolved_connection_id: str | None,
    ) -> dict | None:
        """
        Validate an Agent-generated MCP tool call.

        Returns None when valid.

        Returns an error dictionary when invalid.
        """

        # ---------------------------------------------------------
        # 1. Verify the tool exists
        # ---------------------------------------------------------

        if tool_name not in available_tool_names:
            return {
                "error": (
                    f"Unknown MCP tool '{tool_name}'. "
                    "Only use tools returned by the MCP tool list."
                )
            }

        # ---------------------------------------------------------
        # 2. Verify arguments are an object
        # ---------------------------------------------------------

        if not isinstance(arguments, dict):
            return {
                "error": (
                    f"Invalid arguments for tool '{tool_name}'. "
                    "Tool arguments must be a JSON object."
                )
            }

        # ---------------------------------------------------------
        # 3. Enforce deterministic database resolution
        # ---------------------------------------------------------

        if resolved_connection_id:
            requested_connection_id = arguments.get(
                "connection_id"
            )

            if requested_connection_id:
                if requested_connection_id != resolved_connection_id:
                    return {
                        "error": (
                            "The application resolved this question "
                            "to a specific database, but the requested "
                            "tool call targets a different database. "
                            f"Use connection_id "
                            f"'{resolved_connection_id}'."
                        )
                    }

        return None

    async def process(
            self,
            question: str,
            user_id: str,
            connection_id: str | None = None,
            messages: list[dict] | None = None,
        ) -> dict:
        question = question.strip()
        messages = messages or []

        if not question:
            raise ValueError("Question cannot be empty")

        # ---------------------------------------------------------
        # Deterministic database resolution
        # ---------------------------------------------------------

        database_resolution = await self._resolve_database(
            question,
            user_id,
            connection_id,
        )

        if database_resolution:
            if database_resolution["status"] == "ambiguous":
                return {
                    "question": question,
                    "answer": database_resolution["message"],
                }

            if database_resolution["status"] == "resolved":
                resolved_connection_id = (
                    database_resolution["connection_id"]
                )

                resolved_connection_name = (
                    database_resolution["connection_name"]
                )

        else:
            resolved_connection_id = None
            resolved_connection_name = None

        # ---------------------------------------------------------
        # Discover MCP tools dynamically
        # ---------------------------------------------------------

        tools = await self._get_tools()

        available_tool_names = {
            tool["function"]["name"]
            for tool in tools
        }

        messages_for_llm = [
            {
                "role": "system",
                "content": (
                    "You are the DataMCP AI assistant.\n\n"

                    "GENERAL RULES:\n"
                    "- Answer general questions directly.\n"
                    "- Never invent database information.\n"
                    "- When database information is required, "
                    "use the available MCP tools.\n"
                    "- When information from the user's connected Notion workspace "
                    "is requested, use the available Notion MCP tools.\n"
                    "- Never claim that you cannot access Notion when a Notion MCP "
                    "tool is available.\n\n"

                    "DATABASE SELECTION:\n"
                    "- DataMCP may have multiple databases connected.\n"
                    "- Never assume a database connection ID.\n"
                    "- Always use a connection ID returned by an MCP tool.\n"
                    "- If the user explicitly identifies a database, "
                    "use that database.\n"
                    "- If a database has already been deterministically "
                    "resolved by the application, use that database "
                    "and do not switch to another database.\n"
                    "- If the question is ambiguous between multiple "
                    "databases, do not guess.\n\n"

                    "KNOWLEDGE RETRIEVAL:\n"
                    "- Use search_knowledge when the question asks about the user's "
                    "saved knowledge, previous plans, project decisions, architecture, "
                    "documentation, notes, or other information that may exist in "
                    "their connected knowledge sources.\n"
                    "- When the user asks about a previous conversation, "
                    "earlier discussion, past work, what was discussed before, "
                    "what they were working on, what was decided previously, "
                    "or asks to continue from where they left off, treat the "
                    "request as a saved-knowledge retrieval request.\n"
                    "- Use search_knowledge to retrieve relevant information "
                    "from previously saved conversations and knowledge sources, "
                    "even when the user does not mention Notion or any specific "
                    "knowledge provider.\n"
                    "- Do not assume that a new chat means previously saved "
                    "knowledge is unavailable.\n"
                    "- When answering questions about the user's own DataMCP project "
                    "or previously saved project information, prefer search_knowledge "
                    "over general knowledge.\n"
                    "- Do not answer from general knowledge when the requested "
                    "information may be available in the user's saved knowledge.\n"
                    "- Use search_notion when the user explicitly asks to find or "
                    "search pages in their Notion workspace.\n"
                    "- Use get_notion_page when the content of a specific Notion "
                    "page is required.\n"
                    "- Use create_notion_page when the user explicitly asks to "
                    "create a new Notion page.\n"
                    "- Use update_notion_page when the user explicitly asks to "
                    "modify an existing Notion page.\n"
                    "- Do not invent Notion page IDs.\n"
                    "- For Notion search requests, use the user's query as the "
                    "search query whenever possible.\n\n"

                    "NOTION CONNECTION CHECK:"
                    "- Before creating or updating anything in Notion, first use the notion_connection_status tool."
                    "- If Notion is not connected, do not call create_notion_page or update_notion_page."
                    "- Instead, tell the user that Notion isn't connected to DataMCP and that they need to connect Notion before storing anything."
                    "- If Notion is connected, continue with the requested Notion operation."

                    "CONVERSATION SAVING:\n"
                    "- When the user asks to save, store, document, or remember "
                    "the current conversation/discussion in Notion, use the "
                    "conversation history provided to you.\n"
                    "- Treat the conversation history as the source of truth "
                    "for what was discussed.\n"
                    "- Do NOT summarize only the current user message.\n"
                    "- Do not include the user's request to save the conversation "
                    "as a topic in the summary unless it is itself relevant to the "
                    "conversation's subject.\n"
                    "- Summarize the actual previous discussion, including "
                    "important topics, decisions, verified results, technical "
                    "progress, problems, solutions, and next steps.\n"
                    "- Generate a concise, descriptive Notion page title based "
                    "on the actual subject of the conversation.\n"
                    "- The title must describe the subject rather than using "
                    "a generic title such as 'ChatGPT Conversation - <date>'.\n"
                    "- Create the Notion page using the generated descriptive "
                    "title and the summarized conversation.\n"
                    "- Format the Notion summary as clean, human-readable plain text.\n"
                    "- Do not use Markdown headings such as '#', '##', or '###'.\n"
                    "- Do not use Markdown bullet markers such as '-', '*', or '+'.\n"
                    "- Do not use Markdown numbered lists such as '1.', '2.', or '3.'.\n"
                    "- Do not use Markdown tables.\n"
                    "- Use simple section titles followed by short paragraphs when "
                    "organizing the summary.\n"
                    "- Use plain text labels such as 'PostgreSQL:', 'MySQL:', "
                    "and 'MongoDB:' when appropriate.\n"
                    "- Keep the summary natural and readable as if a person wrote "
                    "notes directly in Notion.\n"
                    "- Do not save the full transcript unless the user explicitly "
                    "asks to save the full transcript or conversation history.\n"
                    "- If the user explicitly asks for the full transcript, "
                    "preserve the conversation history rather than summarizing it.\n"
                    "- After creating the page, return the generated title and "
                    "Notion page URL.\n\n"

                    "SCHEMA DISCOVERY:\n"
                    "- Use search_schema for semantic or ambiguous "
                    "schema questions.\n"
                    "- Use get_database_schema when the complete schema "
                    "is required.\n"
                    "- Use describe_table when detailed information "
                    "about a specific table is required.\n"
                    "- Use get_sample_data when actual example rows "
                    "are useful.\n\n"

                    "QUERY EXECUTION:\n"
                    "- For PostgreSQL and MySQL, use execute_read_query.\n"
                    "- For MongoDB, use execute_mongodb_query.\n"
                    "- Only perform read-only operations.\n"
                    "- For SQL databases, use the discovered schema to "
                    "construct SQL.\n"
                    "- For MongoDB, use the discovered schema to identify "
                    "the collection and fields, then construct a structured "
                    "MongoDB filter.\n"
                    "- Never use execute_read_query for MongoDB.\n"
                    "- Never use execute_mongodb_query for PostgreSQL or MySQL.\n"
                    "- Verify table or collection names and fields from tools "
                    "before querying.\n"
                    "- When SQL relationships exist, use the documented "
                    "foreign keys to construct JOINs.\n"
                    "- Never invent table names, collection names, column names, "
                    "field names, or values.\n\n"

                    "TOOL USAGE:\n"
                    "- Only call tools that are provided in the available "
                    "MCP tool list.\n"
                    "- Provide valid JSON arguments matching the tool schema.\n"
                    "- Do not invent connection IDs.\n\n"

                    "RESPONSE:\n"
                    "- Give a concise natural-language answer.\n"
                    "- When useful, include the relevant data in a table.\n"
                ),
            }
        ]

        if resolved_connection_id:
            messages_for_llm.append(
                {
                    "role": "system",
                    "content": (
                        "APPLICATION DATABASE RESOLUTION:\n"
                        f"The application resolved this question to "
                        f"the database '{resolved_connection_name}' "
                        f"with connection ID "
                        f"'{resolved_connection_id}'.\n"
                        "Use ONLY this connection for database "
                        "operations for this question.\n"
                        "If a tool requires connection_id, it MUST be "
                        f"'{resolved_connection_id}'."
                    ),
                }
            )

        if messages:
            for message in messages:
                role = message.get("role")
                content = message.get("content")

                if role in {"user", "assistant"} and content:
                    messages_for_llm.append(
                        {
                            "role": role,
                            "content": content,
                        }
                    )

        else:
            messages_for_llm.append(
                {
                    "role": "user",
                    "content": question,
                }
            )
        
        # ---------------------------------------------------------
        # Agent tool loop
        # ---------------------------------------------------------

        for _ in range(self.MAX_TOOL_ITERATIONS):
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages_for_llm,
                tools=tools,
                tool_choice="auto",
            )

            message = response.choices[0].message

            if not message.tool_calls:
                answer = message.content or ""

                answer = answer.strip()

                return {
                    "question": question,
                    "answer": answer,
                }

            messages_for_llm.append(message)

            for tool_call in message.tool_calls:

                tool_name = tool_call.function.name

                # -------------------------------------------------
                # Parse tool arguments
                # -------------------------------------------------

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                    )

                except json.JSONDecodeError as error:
                    tool_result = {
                        "error": (
                            "Invalid JSON tool arguments: "
                            f"{str(error)}"
                        )
                    }

                else:

                    # ---------------------------------------------
                    # Inject the application-resolved database
                    # ---------------------------------------------

                    if (
                        resolved_connection_id
                        and tool_name not in {
                            "health_check",
                            "list_connections",
                        }
                    ):
                        arguments["connection_id"] = resolved_connection_id

                    # ---------------------------------------------
                    # Validate the Agent-generated tool call
                    # ---------------------------------------------

                    validation_error = self._validate_tool_call(
                        tool_name=tool_name,
                        arguments=arguments,
                        available_tool_names=available_tool_names,
                        resolved_connection_id=resolved_connection_id,
                    )

                    if validation_error:
                        tool_result = validation_error

                    else:
                        try:
                            result = await self._execute_tool(
                                tool_name=tool_name,
                                arguments=arguments,
                                user_id=user_id,
                            )

                            tool_result = self._serialize_tool_result(
                                result
                            )

                        except Exception as error:
                            tool_result = {
                                "error": (
                                    f"MCP tool '{tool_name}' failed: "
                                    f"{str(error)}"
                                )
                            }

                # -------------------------------------------------
                # Ensure tool result is JSON/text
                # -------------------------------------------------

                if not isinstance(tool_result, str):
                    tool_result = json.dumps(
                        tool_result,
                        default=str,
                    )

                messages_for_llm.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result,
                    }
                )

        raise ValueError(
            "Agent reached the maximum number of tool iterations"
        )


agent_service = AgentService()