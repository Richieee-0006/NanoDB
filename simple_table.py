import itertools
from random import Random
from typing import Sequence, Any, Iterable, Mapping

from nanodb import Table, Column, ColumnType, DataType, Row, Value


class SimpleTable(Table):
    """
    A simplified abstraction layer over the core Table class.
    
    This class is designed for rapid prototyping and ease of use. It 
    automatically handles primary key generation using a random integer 
    '_id' column and defaults most user-provided columns to the TEXT data type.
    """

    def __init__(self, name: str, column_names: Sequence[str]):
        """
        Initialize a SimpleTable with a name and a set of text column names.
        
        This constructor automatically prepends an '_id' column to the schema,
        sets it as the primary key, and configures it to be NOT NULL and UNIQUE.
        All other columns provided in `column_names` are created as DataType.TEXT.
        
        Args:
            name (str): The name of the table.
            column_names (Sequence[str]): List of names for the data columns.
        """
        # 1. Define the mandatory Primary Key column.
        columns = [Column("_id", ColumnType(DataType.INT, not_null=True, unique=True))]
        
        # 2. Append the user-requested text columns.
        for column_name in column_names:
            columns.append(Column(column_name, ColumnType(DataType.TEXT)))
            
        # 3. Call the parent Table constructor.
        super().__init__(name, columns=columns, primary_key=["_id"])
        
        # 4. Initialize a random number generator for ID generation.
        self._id_generator = Random()

    def insert(self, column_names: Sequence[str], values: Row) -> None:
        """
        Overridden insert method to prevent manual ID insertion.
        
        SimpleTable manages its own IDs. Users are encouraged to use 
        `add_row` instead of the lower-level `insert` method.
        
        Raises:
            NotImplementedError: Always, to steer users towards add_row.
        """
        raise NotImplementedError("Use add_row instead of insert for SimpleTable.")

    def add_row(self, *args: str) -> None:
        """
        Add a new row to the table with an automatically generated ID.
        
        This method accepts a variable number of string arguments, each 
        representing a value for one of the user-defined columns. It 
        generates a large random integer for the '_id' column and 
        performs the underlying insertion.
        
        Args:
            *args (str): Values for the columns (excluding the _id).
        """
        # Convert variadic args to a list so we can modify it.
        values: list[Any] = list(args)
        
        # Insert a random ID at the start of the values list (index 0).
        # We use a large range to minimize the chance of collisions.
        values.insert(0, self._id_generator.randint(0, 1_000_000_000_000))
        
        # Retrieve all column names (including _id) to satisfy the parent insert method.
        names = [column.name for column in self.columns]
        
        # Execute the parent class's insertion logic.
        super().insert(column_names=names, values=tuple(values))

    def add_rows(self, *args: Sequence[str]) -> None:
        """
        Batch add multiple rows to the table.
        
        Args:
            *args (Sequence[str]): Multiple sequences of values to be added as rows.
        """
        # Iterate through each provided row and delegate to add_row.
        for row in args:
            self.add_row(*row)

    def iter_rows_as_dict(self) -> Iterable[Mapping[str, Value]]:
        """
        Iterate over the table's data, yielding each row as a dictionary.
        
        This is a convenience method for consuming data in a format 
        that is easier to use in many Python contexts (e.g., JSON export).
        
        Returns:
            Iterable[Mapping[str, Value]]: A generator yielding (col_name: value) maps.
        """
        # Use a generator expression to lazily convert rows to mappings.
        return (self._row_to_mapping(row) for row in self)


if __name__ == "__main__":
    # Internal demonstration of SimpleTable capabilities.
    table = SimpleTable("person", ["name", "phone"])
    
    # Adding single and multiple rows.
    table.add_row("Petr", "123 456 789")
    table.add_rows(("Jan", "123 456 000"), ("Anna", "123 456 999"))
    
    # Displaying results in various formats.
    print("ASCII Table Output:")
    print(table.to_text())
    
    print("\nDictionary Iterator Output:")
    print(list(table.iter_rows_as_dict()))
    
    print("\nColumn Extraction Output (name):")
    print(table.get_column("name"))
