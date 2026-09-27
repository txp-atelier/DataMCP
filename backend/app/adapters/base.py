from abc import ABC, abstractmethod


class DatabaseAdapter(ABC):

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    @abstractmethod
    def test_connection(self) -> bool:
        """Test whether the database connection works."""
        raise NotImplementedError

    @abstractmethod
    def get_schema(self) -> dict:
        """Return a normalized representation of the database schema."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        raise NotImplementedError

    def execute_read_query(
            self,
            query: str,
    ) -> list[dict]:
        raise NotImplementedError