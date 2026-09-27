"use client";

import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
    role: "user" | "assistant";
    content: string;
};

type Database = {
    id: string;
    name: string;
    database_type: string;
    status: string;
};

function cleanMongoIds(text: string) {
    return text.replace(
        /\b(?:[0-9a-fA-F]\s*){24}\b/g,
        (match) => match.replace(/\s+/g, "")
    );
}

export default function Home() {
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [databases, setDatabases] = useState<Database[]>([]);
    const [selectedDatabaseId, setSelectedDatabaseId] = useState<
        string | null
    >(null);

    const [showAddDatabase, setShowAddDatabase] = useState(false);

    const [databaseName, setDatabaseName] = useState("");
    const [databaseType, setDatabaseType] = useState("postgresql");
    const [connectionString, setConnectionString] = useState("");
    const [addingDatabase, setAddingDatabase] = useState(false);
    const [databaseError, setDatabaseError] = useState("");

    const [deletingDatabaseId, setDeletingDatabaseId] = useState<string | null>(null);
    const [databaseActionError, setDatabaseActionError] = useState("");

    const [openDatabaseMenuId, setOpenDatabaseMenuId] = useState<string | null>(null);
    const [testingDatabaseId, setTestingDatabaseId] = useState<string | null>(null);

    const [editingDatabase, setEditingDatabase] =
        useState<Database | null>(null);

    const [editDatabaseName, setEditDatabaseName] =
        useState("");

    const [editDatabaseType, setEditDatabaseType] =
        useState("postgresql");

    const [editConnectionString, setEditConnectionString] =
        useState("");

    const [savingDatabase, setSavingDatabase] =
        useState(false);

    const [editDatabaseError, setEditDatabaseError] =
        useState("");

    const [notionConnected, setNotionConnected] = useState(false);
    const [notionLoading, setNotionLoading] = useState(true);
    const [notionDisconnecting, setNotionDisconnecting] = useState(false);

    useEffect(() => {
        async function loadDatabases() {
            try {
                const response = await fetch(
                    "http://localhost:8000/connections?user_id=demo-user"
                );

                if (!response.ok) {
                    throw new Error("Failed to load databases");
                }

                const data = await response.json();
                setDatabases(data);
            } catch (error) {
                console.error("Failed to load databases:", error);
            }
        }

        loadDatabases();
    }, []);

    useEffect(() => {
        async function loadNotionStatus() {
            try {
                const response = await fetch(
                    "http://localhost:8000/integrations/notion/status"
                );

                if (!response.ok) {
                    throw new Error(
                        "Failed to load Notion status"
                    );
                }

                const data = await response.json();

                setNotionConnected(
                    data.connected === true
                );
            } catch (error) {
                console.error(
                    "Failed to load Notion status:",
                    error
                );
            } finally {
                setNotionLoading(false);
            }
        }

        loadNotionStatus();
    }, []);

    useEffect(() => {
        function handleNotionOAuthMessage(event: MessageEvent) {
            if (event.origin !== "http://localhost:8000") {
                return;
            }

            if (event.data?.type !== "NOTION_OAUTH_SUCCESS") {
                return;
            }

            setNotionConnected(true);
        }

        window.addEventListener(
            "message",
            handleNotionOAuthMessage
        );

        return () => {
            window.removeEventListener(
                "message",
                handleNotionOAuthMessage
            );
        };
    }, []);

    async function addDatabase() {
        if (
            !databaseName.trim() ||
            !connectionString.trim() ||
            addingDatabase
        ) {
            return;
        }

        setAddingDatabase(true);
        setDatabaseError("");

        try {
            const response = await fetch(
                "http://localhost:8000/connections",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        user_id: "demo-user",
                        name: databaseName.trim(),
                        database_type: databaseType,
                        connection_string: connectionString.trim(),
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Failed to add database"
                );
            }

            setDatabases((current) => [
                ...current,
                data,
            ]);

            setDatabaseName("");
            setDatabaseType("postgresql");
            setConnectionString("");
            setShowAddDatabase(false);
        } catch (error) {
            setDatabaseError(
                error instanceof Error
                    ? error.message
                    : "Failed to add database."
            );
        } finally {
            setAddingDatabase(false);
        }
    }

    async function deleteDatabase(databaseId: string) {
        if (deletingDatabaseId) {
            return;
        }

        const confirmed = window.confirm(
            "Are you sure you want to delete this database connection?"
        );

        if (!confirmed) {
            return;
        }

        setDeletingDatabaseId(databaseId);
        setDatabaseActionError("");

        try {
            const response = await fetch(
                `http://localhost:8000/connections/${databaseId}`,
                {
                    method: "DELETE",
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Failed to delete database"
                );
            }

            setDatabases((current) =>
                current.filter(
                    (database) => database.id !== databaseId
                )
            );

            if (selectedDatabaseId === databaseId) {
                setSelectedDatabaseId(null);
            }
        } catch (error) {
            setDatabaseActionError(
                error instanceof Error
                    ? error.message
                    : "Failed to delete database."
            );
        } finally {
            setDeletingDatabaseId(null);
        }
    }

    async function testDatabase(databaseId: string) {
        if (testingDatabaseId) {
            return;
        }

        setTestingDatabaseId(databaseId);
        setDatabaseActionError("");

        try {
            const response = await fetch(
                `http://localhost:8000/connections/${databaseId}/test`,
                {
                    method: "POST",
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Failed to test database"
                );
            }

            setDatabases((current) =>
                current.map((database) =>
                    database.id === databaseId
                        ? {
                            ...database,
                            status: data.status,
                        }
                        : database
                )
            );
        } catch (error) {
            setDatabaseActionError(
                error instanceof Error
                    ? error.message
                    : "Failed to test database."
            );
        } finally {
            setTestingDatabaseId(null);
        }
    }

    function openEditDatabase(database: Database) {
        setEditingDatabase(database);
        setEditDatabaseName(database.name);
        setEditDatabaseType(database.database_type);
        setEditConnectionString("");
        setEditDatabaseError("");
        setOpenDatabaseMenuId(null);
    }

    async function saveDatabaseChanges() {
        if (
            !editingDatabase ||
            !editDatabaseName.trim() ||
            savingDatabase
        ) {
            return;
        }

        setSavingDatabase(true);
        setEditDatabaseError("");

        try {
            const response = await fetch(
                `http://localhost:8000/connections/${editingDatabase.id}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        name: editDatabaseName.trim(),
                        database_type: editDatabaseType,
                        connection_string:
                            editConnectionString.trim(),
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Failed to update database"
                );
            }

            setDatabases((current) =>
                current.map((database) =>
                    database.id === data.id
                        ? data
                        : database
                )
            );

            if (selectedDatabaseId === data.id) {
                setSelectedDatabaseId(data.id);
            }

            setEditingDatabase(null);
        } catch (error) {
            setEditDatabaseError(
                error instanceof Error
                    ? error.message
                    : "Failed to update database."
            );
        } finally {
            setSavingDatabase(false);
        }
    }

    async function askDataMCP() {
        const trimmedQuestion = question.trim();

        if (!trimmedQuestion || loading) {
            return;
        }

        setMessages((current) => [
            ...current,
            {
                role: "user",
                content: trimmedQuestion,
            },
        ]);

        setQuestion("");
        setLoading(true);

        try {
            const response = await fetch(
                "http://localhost:8000/agent",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        question: trimmedQuestion,
                        connection_id: selectedDatabaseId,
                        messages: [
                            ...messages,
                            {
                                role: "user",
                                content: trimmedQuestion,
                            },
                        ],
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Something went wrong"
                );
            }

            setMessages((current) => [
                ...current,
                {
                    role: "assistant",
                    content: data.answer,
                },
            ]);
        } catch (error) {
            setMessages((current) => [
                ...current,
                {
                    role: "assistant",
                    content:
                        error instanceof Error
                            ? error.message
                            : "Unable to connect to DataMCP.",
                },
            ]);
        } finally {
            setLoading(false);
        }
    }

async function connectNotion() {
    try {
        const response = await fetch(
            "http://localhost:8000/integrations/notion/authorize"
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Failed to start Notion authorization"
            );
        }

        if (!data.authorization_url) {
            throw new Error(
                "Notion authorization URL was not returned"
            );
        }

        const width = 600;
        const height = 750;

        const left =
            window.screenX +
            (window.outerWidth - width) / 2;

        const top =
            window.screenY +
            (window.outerHeight - height) / 2;

        window.open(
            data.authorization_url,
            "notion-oauth",
            `width=${width},height=${height},left=${left},top=${top}`
        );
    } catch (error) {
        console.error(
            "Failed to connect Notion:",
            error
        );

        window.alert(
            error instanceof Error
                ? error.message
                : "Failed to connect Notion."
        );
    }
}

    async function disconnectNotion() {
        if (notionDisconnecting) {
            return;
        }

        const confirmed = window.confirm(
            "Disconnect Notion from DataMCP?"
        );

        if (!confirmed) {
            return;
        }

        setNotionDisconnecting(true);

        try {
            const response = await fetch(
                "http://localhost:8000/integrations/notion/disconnect",
                {
                    method: "POST",
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    "Failed to disconnect Notion"
                );
            }

            setNotionConnected(false);
        } catch (error) {
            console.error(
                "Failed to disconnect Notion:",
                error
            );

            window.alert(
                error instanceof Error
                    ? error.message
                    : "Failed to disconnect Notion."
            );
        } finally {
            setNotionDisconnecting(false);
        }
    }

    function handleKeyDown(
        event: React.KeyboardEvent<HTMLInputElement>
    ) {
        if (event.key === "Enter") {
            askDataMCP();
        }
    }

    return (
        <main className="app-shell">
            <aside className="sidebar">
                <div className="brand">
                    <div className="brand-icon">D</div>

                    <div>
                        <h1>DataMCP</h1>
                        <p>AI Data Assistant</p>
                    </div>
                </div>

                <div className="sidebar-section">
                    <div className="section-heading">
                        <span>Connected databases</span>

                        <span className="database-count">
                            {databases.length}
                        </span>
                    </div>

                    <div className="database-list">
                        {databases.map((database) => (
                            <div
                                className={`database-card ${selectedDatabaseId === database.id
                                    ? "selected"
                                    : ""
                                    } ${openDatabaseMenuId === database.id
                                        ? "menu-open"
                                        : ""
                                    }`}
                                onClick={() =>
                                    setSelectedDatabaseId(
                                        selectedDatabaseId === database.id ? null : database.id
                                    )
                                }
                                key={database.id}
                            >
                                <div className="database-icon">
                                    {database.database_type === "mongodb"
                                        ? "M"
                                        : database.database_type === "mysql"
                                            ? "Y"
                                            : "P"}
                                </div>

                                <div className="database-info">
                                    <strong>{database.name}</strong>

                                    <span>
                                        {database.database_type === "mongodb"
                                            ? "Document"
                                            : "Relational"}
                                    </span>
                                </div>

                                <span
                                    className={`connection-status ${database.status !== "connected"
                                        ? "offline"
                                        : ""
                                        }`}
                                />

                                <div className="database-menu">
                                    <button
                                        type="button"
                                        className="database-menu-button"
                                        onClick={(event) => {
                                            event.stopPropagation();

                                            setOpenDatabaseMenuId((current) =>
                                                current === database.id
                                                    ? null
                                                    : database.id
                                            );
                                        }}
                                        title="Database actions"
                                    >
                                        ⋮
                                    </button>

                                    {openDatabaseMenuId === database.id && (
                                        <div
                                            className="database-menu-dropdown"
                                            onClick={(event) => event.stopPropagation()}
                                        >
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setOpenDatabaseMenuId(null);
                                                    testDatabase(database.id);
                                                }}
                                                disabled={testingDatabaseId === database.id}
                                            >
                                                {testingDatabaseId === database.id
                                                    ? "Testing..."
                                                    : "Test connection"}
                                            </button>

                                            <button
                                                type="button"
                                                onClick={() => openEditDatabase(database)}
                                            >
                                                Edit
                                            </button>

                                            <button
                                                type="button"
                                                className="danger"
                                                onClick={() => {
                                                    setOpenDatabaseMenuId(null);
                                                    deleteDatabase(database.id);
                                                }}
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <button
                        className="add-database-button"
                        onClick={() => setShowAddDatabase(true)}
                    >
                        <span>+</span>
                        Add database
                    </button>
                </div>

                <div className="sidebar-footer">
                    <div className="system-status">
                        <span className="status-dot" />

                        <div>
                            <strong>System online</strong>
                            <span>All services operational</span>
                        </div>
                    </div>
                </div>
            </aside>

            <section className="main-panel">
                <header className="topbar">
                    <div>
                        <span className="eyebrow">
                            MULTI-DATABASE INTELLIGENCE
                        </span>

                        <h2>Ask your data</h2>
                    </div>

                    <div className="topbar-actions">
                        {messages.length > 0 && (
                            <button
                                className="new-chat-button"
                                onClick={() => setMessages([])}
                            >
                                + New chat
                            </button>
                        )}

                        {!notionLoading && (
                            notionConnected ? (
                                <button
                                    type="button"
                                    className="notion-connected-button"
                                    onClick={disconnectNotion}
                                    disabled={notionDisconnecting}
                                >
                                    {notionDisconnecting
                                        ? "Disconnecting..."
                                        : "✓ Notion Connected"}
                                </button>
                            ) : (
                                <button
                                    type="button"
                                    className="notion-connect-button"
                                    onClick={connectNotion}
                                >
                                    Connect Notion
                                </button>
                            )
                        )}

                        <div className="agent-status">
                            <span className="status-dot" />
                            Agent ready
                        </div>
                    </div>
                </header>

                <div className="chat-container">
                    {messages.length === 0 ? (
                        <div className="welcome">
                            <div className="welcome-icon">✦</div>

                            <h3>What would you like to know?</h3>

                            <p>
                                Ask questions about your connected databases
                                in natural language.
                            </p>

                            <div className="suggestions">
                                <button
                                    onClick={() => {
                                        setQuestion(
                                            "How many customers are there in PostgreSQL?"
                                        );

                                        setTimeout(() => {
                                            askDataMCP();
                                        }, 0);
                                    }}
                                >
                                    How many customers are there?
                                </button>

                                <button
                                    onClick={() => {
                                        setQuestion(
                                            "Show me all customers in MongoDB."
                                        );

                                        setTimeout(() => {
                                            askDataMCP();
                                        }, 0);
                                    }}
                                >
                                    Show me MongoDB customers
                                </button>

                                <button
                                    onClick={() => {
                                        setQuestion(
                                            "How many customers are there in MySQL?"
                                        );

                                        setTimeout(() => {
                                            askDataMCP();
                                        }, 0);
                                    }}
                                >
                                    Query MySQL
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="messages">
                            {messages.map((message, index) => (
                                <div
                                    className={`message-row ${message.role}`}
                                    key={index}
                                >
                                    <div className="message-avatar">
                                        {message.role === "user" ? "U" : "D"}
                                    </div>

                                    <div className="message-content">
                                        <span className="message-role">
                                            {message.role === "user"
                                                ? "You"
                                                : "DataMCP"}
                                        </span>

                                        <div className="message-text">
                                            {message.role === "assistant" ? (
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                >
                                                    {cleanMongoIds(
                                                        message.content
                                                    )}
                                                </ReactMarkdown>
                                            ) : (
                                                <p>{message.content}</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {loading && (
                                <div className="message-row assistant">
                                    <div className="message-avatar">
                                        D
                                    </div>

                                    <div className="message-content">
                                        <span className="message-role">
                                            DataMCP
                                        </span>

                                        <div className="typing">
                                            <span />
                                            <span />
                                            <span />
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="composer-wrapper">
                    <div className="composer">
                        <input
                            value={question}
                            onChange={(event) =>
                                setQuestion(event.target.value)
                            }
                            onKeyDown={handleKeyDown}
                            placeholder="Ask anything about your data..."
                            disabled={loading}
                        />

                        <button
                            onClick={askDataMCP}
                            disabled={
                                loading || !question.trim()
                            }
                        >
                            {loading ? "..." : "↑"}
                        </button>
                    </div>

                    <p className="composer-hint">
                        DataMCP uses AI agents, MCP, and RAG to answer
                        questions across your connected databases.
                    </p>
                </div>
            </section>

            {showAddDatabase && (
                <div
                    className="modal-overlay"
                    onClick={() => setShowAddDatabase(false)}
                >
                    <div
                        className="database-modal"
                        onClick={(event) => event.stopPropagation()}
                    >
                        <div className="modal-header">
                            <div>
                                <span className="eyebrow">
                                    DATABASE MANAGEMENT
                                </span>

                                <h3>Add database</h3>
                            </div>

                            <button
                                className="modal-close"
                                onClick={() =>
                                    setShowAddDatabase(false)
                                }
                            >
                                ×
                            </button>
                        </div>

                        <div className="database-form">
                            <label>
                                <span>Database name</span>

                                <input
                                    type="text"
                                    value={databaseName}
                                    onChange={(event) =>
                                        setDatabaseName(event.target.value)
                                    }
                                    placeholder="My Production Database"
                                />
                            </label>

                            <label>
                                <span>Database type</span>

                                <select
                                    value={databaseType}
                                    onChange={(event) =>
                                        setDatabaseType(event.target.value)
                                    }
                                >
                                    <option value="postgresql">
                                        PostgreSQL
                                    </option>

                                    <option value="mysql">
                                        MySQL
                                    </option>

                                    <option value="mongodb">
                                        MongoDB
                                    </option>
                                </select>
                            </label>

                            <label>
                                <span>Connection string</span>

                                <input
                                    type="text"
                                    value={connectionString}
                                    onChange={(event) =>
                                        setConnectionString(event.target.value)
                                    }
                                    placeholder="postgresql+psycopg://user:password@host:5432/database"
                                />
                            </label>

                            {databaseError && (
                                <div className="database-form-error">
                                    {databaseError}
                                </div>
                            )}

                            <div className="form-actions">
                                <button
                                    className="secondary-button"
                                    onClick={() =>
                                        setShowAddDatabase(false)
                                    }
                                >
                                    Cancel
                                </button>

                                <button
                                    className="primary-button"
                                    type="button"
                                    onClick={addDatabase}
                                    disabled={
                                        addingDatabase ||
                                        !databaseName.trim() ||
                                        !connectionString.trim()
                                    }
                                >
                                    {addingDatabase ? "Connecting..." : "Add database"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {editingDatabase && (
                <div
                    className="modal-overlay"
                    onClick={() => setEditingDatabase(null)}
                >
                    <div
                        className="database-modal"
                        onClick={(event) => event.stopPropagation()}
                    >
                        <div className="modal-header">
                            <div>
                                <span className="eyebrow">
                                    DATABASE MANAGEMENT
                                </span>

                                <h3>Edit database</h3>
                            </div>

                            <button
                                className="modal-close"
                                onClick={() => setEditingDatabase(null)}
                            >
                                ×
                            </button>
                        </div>

                        <div className="database-form">
                            {editDatabaseError && (
                                <div className="database-form-error">
                                    {editDatabaseError}
                                </div>
                            )}

                            <label>
                                <span>Database name</span>

                                <input
                                    type="text"
                                    value={editDatabaseName}
                                    onChange={(event) =>
                                        setEditDatabaseName(
                                            event.target.value
                                        )
                                    }
                                />
                            </label>

                            <label>
                                <span>Database type</span>

                                <select
                                    value={editDatabaseType}
                                    onChange={(event) =>
                                        setEditDatabaseType(
                                            event.target.value
                                        )
                                    }
                                >
                                    <option value="postgresql">
                                        PostgreSQL
                                    </option>

                                    <option value="mysql">
                                        MySQL
                                    </option>

                                    <option value="mongodb">
                                        MongoDB
                                    </option>
                                </select>
                            </label>

                            <label>
                                <span>Connection string</span>

                                <input
                                    type="text"
                                    value={editConnectionString}
                                    onChange={(event) =>
                                        setEditConnectionString(
                                            event.target.value
                                        )
                                    }
                                    placeholder="Enter a new connection string"
                                />

                                <small className="database-form-hint">
                                    Leave blank to keep the existing
                                    connection string.
                                </small>
                            </label>

                            <div className="form-actions">
                                <button
                                    className="secondary-button"
                                    type="button"
                                    onClick={() =>
                                        setEditingDatabase(null)
                                    }
                                >
                                    Cancel
                                </button>

                                <button
                                    className="primary-button"
                                    type="button"
                                    onClick={saveDatabaseChanges}
                                    disabled={
                                        savingDatabase ||
                                        !editDatabaseName.trim()
                                    }
                                >
                                    {savingDatabase
                                        ? "Saving..."
                                        : "Save changes"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
}