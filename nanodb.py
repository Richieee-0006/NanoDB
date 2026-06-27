from datetime import date
from decimal import Decimal
from enum import Enum
from collections.abc import Collection, Sequence
from multiprocessing.spawn import get_command_line
from typing import TypeAlias, Iterator, Callable, Mapping

# Type aliases for better readability and consistent type checking across the library.
# Value represents any scalar data type that can be stored in a table cell.
Value: TypeAlias = None | int | Decimal | str | date
# Row represents a single record in a table, stored as an immutable tuple of values.
Row: TypeAlias = tuple[Value, ...]

def value_to_text(value: Value) -> str:
    """
    Convert a single database value to its human-readable text representation.
    
    This function handles the conversion of various types (int, Decimal, str, date)
    into a string suitable for display in the CLI. Special care is taken for 
    NULL values (represented as None in Python).
    
    Args:
        value (Value): The database value to convert.
        
    Returns:
        str: "NULL" if the value is None, otherwise the standard string representation.
    """
    # Check for None first to return the SQL-style NULL indicator.
    if value is None:
        return "NULL"
    # For all other types, use Python's built-in string conversion.
    return str(value)


def row_to_texts(row: Row) -> list[str]:
    """
    Convert an entire database row (tuple of values) into a list of strings.
    
    This utility function applies `value_to_text` to every element in a row,
    preparing the data for alignment and display in an ASCII table.
    
    Args:
        row (Row): A tuple of database values.
        
    Returns:
        list[str]: A list of strings corresponding to the values in the row.
    """
    # Use list comprehension to transform every value in the tuple.
    return [value_to_text(value) for value in row]


def compute_column_widths(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[int]:
    """
    Calculate the optimal display width for every column in a table.
    
    The width of a column is determined by the maximum length of either its 
    header name or any value currently stored in that column across all rows.
    
    Args:
        headers (Sequence[str]): The names of the table columns.
        rows (Sequence[Sequence[str]]): The row data, already converted to strings.
        
    Returns:
        list[int]: A list of integers where each index corresponds to the required 
                  width of the column at that index.
    """
    # Initialize widths with the length of the headers.
    widths = [len(header) for header in headers]

    # Iterate through each row and each cell to find the maximum width.
    for row in rows:
        for i, value in enumerate(row):
            # Update the width at index 'i' if the current value is longer.
            widths[i] = max(widths[i], len(value))

    return widths


def make_separator(widths: Sequence[int]) -> str:
    """
    Generate a horizontal separator line for the ASCII table display.
    
    Constructs a line like "+---+-------+" using the calculated column widths.
    
    Args:
        widths (Sequence[int]): The list of required widths for each column.
        
    Returns:
        str: A formatted separator string.
    """
    # Create segments of dashes for each column, adding padding (+2 for spaces).
    parts = ["-" * (width + 2) for width in widths]
    # Join parts with '+' and wrap with '+' on both ends.
    return "+" + "+".join(parts) + "+"


def make_data_line(values: Sequence[str], widths: Sequence[int]) -> str:
    """
    Format a single row of data as a piped ASCII string.
    
    Constructs a line like "| Val | Data  |" with appropriate padding and alignment.
    
    Args:
        values (Sequence[str]): The string values to display in the line.
        widths (Sequence[int]): The widths for each column to ensure alignment.
        
    Returns:
        str: A formatted data line string.
    """
    # Use f-string formatting to left-align the value within its allocated width.
    cells = [f" {value:<{width}} " for value, width in zip(values, widths)]
    # Join cells with '|' and wrap with '|' on both ends.
    return "|" + "|".join(cells) + "|"

class DataType(Enum):
    """
    Enumeration of supported relational data domains.
    
    This Enum provides a stable set of identifiers for the data types that
    the NanoDB engine knows how to validate and store.
    """
    INT = 0      # Integer values (int)
    DECIMAL = 1  # Fixed-point decimal values (Decimal)
    TEXT = 2     # String values (str)
    DATE = 3     # Date values (datetime.date)


class ColumnType:
    """
    Description of a database column's domain and constraints.
    
    This class acts as a configuration object for a column, specifying 
    what kind of data it holds and what rules (constraints) apply to it.
    """

    def __init__(
        self,
        data_type: DataType,
        not_null: bool = False,
        unique: bool = False,
    ) -> None:
        """
        Initialize a column type definition.
        
        Args:
            data_type (DataType): The expected data type for this column.
            not_null (bool): If True, None (NULL) values are forbidden.
            unique (bool): If True, every non-NULL value in the column must be unique.
        """
        self.data_type = data_type
        self.not_null = not_null
        self.unique = unique


class Column:
    """
    Definition of a single table column, including its name and type.
    
    Combines a name identifier with a ColumnType to fully define a 
    component of a table's schema.
    """

    def __init__(self, name: str, column_type: ColumnType) -> None:
        """
        Initialize a column definition.
        
        Args:
            name (str): The name of the column.
            column_type (ColumnType): The type and constraint configuration.
        """
        self.name = name
        self.column_type = column_type

# Internal mapping used to perform type validation during insertion.
# Maps DataType enums to the corresponding Python classes.
TYPE_INFO: dict[DataType, type] = {
        DataType.INT: int,
        DataType.DECIMAL: Decimal,
        DataType.TEXT: str,
        DataType.DATE: date,
    }


def has_duplicates(items: Collection[str]) -> bool:
    """
    Check if a collection of strings contains any duplicate values.
    
    Used primarily for validating schema definitions (e.g., column names).
    
    Args:
        items (Collection[str]): The collection to check.
        
    Returns:
        bool: True if duplicates exist, False otherwise.
    """
    # Comparing length to the size of a set (which filters duplicates).
    return len(items) != len(set(items))


class Table(Sequence):
    """
    A simple in-memory relational table implementation.
    
    A Table consists of a schema (ordered columns and a primary key) 
    and data (rows stored as tuples). It enforces relational integrity 
    rules during data modification.
    
    The Table class implements the Sequence protocol, meaning it can be 
    treated like a read-only list of rows (supporting len, index access, etc.).
    """

    def __init__(
        self,
        name: str,
        columns: Sequence[Column],
        primary_key: Sequence[str]):
        """
        Initialize a new Table with a name and schema.
        
        This constructor performs extensive validation on the provided schema 
        to ensure it is logically consistent (e.g., unique column names, 
        valid primary key columns).
        
        Args:
            name (str): The name of the table.
            columns (Sequence[Column]): List of column definitions.
            primary_key (Sequence[str]): Column names that form the primary key.
            
        Raises:
            ValueError: If the schema is invalid (empty, duplicate names, unknown PK columns).
        """
        # 1. Basic schema validation.
        if not columns:
            raise ValueError("Table must have at least one column.")

        column_names = [column.name for column in columns]
        if has_duplicates(column_names):
            raise ValueError("Column names must be unique.")

        # 2. Storage initialization.
        self.name = name
        self._columns = columns
        # O(1) maps for performance during validation and joins.
        self._column_map = {column.name: column for column in columns}
        self._column_index = {
            column.name: index for index, column in enumerate(columns)
        }
        self._rows: list[Row] = []

        # 3. Primary Key validation.
        if not primary_key:
            raise ValueError("Primary key must contain at least one column.")

        if has_duplicates(primary_key):
            raise ValueError("Primary key columns must be unique.")

        for col_name in primary_key:
            if col_name not in self._column_map:
                raise ValueError(f"Unknown primary key column {col_name!r}.")

        self._primary_key = tuple(primary_key)

        # 4. Strict Primary Key rules (NOT NULL / UNIQUE requirements).
        if len(self._primary_key) == 1:
            pk_col = self._column_map[self._primary_key[0]]
            if not pk_col.column_type.not_null:
                raise ValueError("Single-column primary key must be NOT NULL.")
            if not pk_col.column_type.unique:
                raise ValueError("Single-column primary key must be UNIQUE.")
        else:
            for col_name in self._primary_key:
                col = self._column_map[col_name]
                if not col.column_type.not_null:
                    raise ValueError(f"Primary key column {col_name!r} must be NOT NULL.")

    @property
    def columns(self) -> Sequence[Column]:
        """
        Returns the table's column definitions in their defined order.
        
        Returns:
            Sequence[Column]: A tuple of the table's columns.
        """
        return tuple(self._columns)

    @property
    def primary_key(self) -> Sequence[str]:
        """
        Returns the names of the columns that form the primary key.
        
        Returns:
            Sequence[str]: The primary key column names.
        """
        return self._primary_key

    def __iter__(self) -> Iterator[Row]:
        """
        Allows iterating over the table's rows.
        
        Returns:
            Iterator[Row]: An iterator over the internal row storage.
        """
        return iter(self._rows)

    def __reversed__(self) -> Iterator[Row]:
        """
        Allows iterating over the table's rows in reverse order.
        
        Returns:
            Iterator[Row]: A reverse iterator over the internal row storage.
        """
        return reversed(self._rows)

    def __len__(self) -> int:
        """
        Returns the total number of rows currently in the table.
        
        Returns:
            int: Row count.
        """
        return len(self._rows)

    def __getitem__(self, index: int) -> Row:
        """
        Provides index-based access to table rows.
        
        Args:
            index (int): The 0-based index of the row.
            
        Returns:
            Row: The row tuple at the specified index.
        """
        return self._rows[index]

    def insert(self, column_names: Sequence[str], values: Row) -> None:
        """
        Insert a new row into the table.
        
        This method performs the following steps:
        1. Validates that column names and values match in length.
        2. Checks that provided column names exist in the schema.
        3. Fills missing columns with None (NULL).
        4. Validates data types and NOT NULL constraints.
        5. Enforces UNIQUE and Primary Key uniqueness across the table.
        
        Args:
            column_names (Sequence[str]): The names of the columns being provided.
            values (Row): The values to insert for those columns.
            
        Raises:
            ValueError: If constraints are violated or input is malformed.
            TypeError: If a value's type doesn't match the schema.
        """
        # Basic input validation.
        if len(column_names) != len(values) or has_duplicates(column_names):
            raise ValueError("Invalid column_names or values for INSERT.")

        for col_name in column_names:
            if col_name not in self._column_map:
                raise ValueError(f"Unknown column {col_name!r}.")

        # Map input values to the correct row structure.
        value_map = dict(zip(column_names, values))
        row_data: list[Value] = []

        for column in self._columns:
            value = value_map.get(column.name, None)
            self._validate_value(column, value)
            row_data.append(value)

        # Final tuple and uniqueness checks.
        new_row: Row = tuple(row_data)
        self._check_unique_constraints(new_row)
        self._check_primary_key_uniqueness(new_row)
        self._rows.append(new_row)

    @staticmethod
    def _validate_value(column: Column, value: Value) -> None:
        """
        Validate a single value against its column's definition.
        
        Checks both for NULL constraints and correct Python types.
        
        Args:
            column (Column): The column definition to check against.
            value (Value): The value to validate.
            
        Raises:
            ValueError: If a NOT NULL constraint is violated.
            TypeError: If the value type is incorrect.
        """
        col_type = column.column_type

        # NULL check.
        if value is None:
            if col_type.not_null:
                raise ValueError(f"Column {column.name!r} cannot be NULL.")
            return

        # Type check using TYPE_INFO mapping.
        expected_type = TYPE_INFO.get(col_type.data_type)
        if not isinstance(value, expected_type):
            raise TypeError(f"Column {column.name!r} expects {expected_type.__name__}, got {type(value).__name__}.")

    def _check_unique_constraints(self, new_row: Row) -> None:
        """
        Enforce UNIQUE constraints for all columns marked as unique.
        
        Iterates through the table to ensure the new value doesn't already exist.
        NULL values are ignored as they are allowed to repeat in UNIQUE columns.
        
        Args:
            new_row (Row): The row tuple being inserted.
            
        Raises:
            ValueError: If a UNIQUE constraint is violated.
        """
        for column in self._columns:
            if not column.column_type.unique:
                continue

            idx = self._column_index[column.name]
            val = new_row[idx]

            if val is None:
                continue

            for row in self._rows:
                if row[idx] == val:
                    raise ValueError(f"UNIQUE constraint violated for column {column.name!r}.")

    def _check_primary_key_uniqueness(self, new_row: Row) -> None:
        """
        Enforce uniqueness for the table's Primary Key.
        
        Extracts the PK components from the new row and checks against all existing rows.
        Also ensures no part of the primary key is NULL.
        
        Args:
            new_row (Row): The row tuple being inserted.
            
        Raises:
            ValueError: If the PK is duplicate or contains NULL.
        """
        pk_idxs = self._indexes_for(self._primary_key)
        new_pk_val = self._extract_key(new_row, pk_idxs)

        if any(v is None for v in new_pk_val):
            raise ValueError("Primary key cannot contain NULL.")

        for row in self._rows:
            if self._extract_key(row, pk_idxs) == new_pk_val:
                raise ValueError("Duplicate primary key.")

    def _indexes_for(self, column_names: Sequence[str]) -> Sequence[int]:
        """
        Helper to map a sequence of column names to their integer indexes.
        
        Args:
            column_names (Sequence[str]): Names of the columns.
            
        Returns:
            Sequence[int]: The corresponding indexes in a row tuple.
        """
        return tuple(self._column_index[name] for name in column_names)

    @staticmethod
    def _extract_key(row: Row, indexes: Sequence[int]) -> Row:
        """
        Helper to extract a subset of values from a row based on indexes.
        
        Args:
            row (Row): The full row tuple.
            indexes (Sequence[int]): The indexes of values to extract.
            
        Returns:
            Row: A tuple containing only the selected values.
        """
        return tuple(row[idx] for idx in indexes)

    def inner_join(self, other: 'Table', other_foreign_key: Sequence[str]) -> 'Table':
        """
        Perform a relational INNER JOIN with another table.
        
        The current table (`self`) is treated as the primary table (referenced),
        and the `other` table is treated as the referencing table. The join
        condition is: self.primary_key = other.other_foreign_key.
        
        Args:
            other (Table): The table to join with.
            other_foreign_key (Sequence[str]): Columns in 'other' that reference self's PK.
            
        Returns:
            Table: A new table containing the combined rows.
        """
        # 1. Verification and Setup.
        self._validate_join_columns(other, other_foreign_key)
        result = self._create_join_result_table(other)
        
        # 2. Performance Optimization: Build a lookup map for self's rows by PK.
        lookup = self._build_primary_key_lookup()
        other_fk_idxs = other._indexes_for(other_foreign_key)

        # 3. Join Loop: Iterate 'other' and match against 'self' via the lookup.
        for other_row in other._rows:
            fk_val = other._extract_key(other_row, other_fk_idxs)

            if not any(v is None for v in fk_val):
                match = lookup.get(fk_val)
                if match is not None:
                    # Combine tuples and store in result.
                    result._rows.append(match + other_row)

        return result

    def to_text(self) -> str:
        """
        Render the table contents as a formatted ASCII grid.
        
        Returns:
            str: The string representation of the table.
        """
        headers = [c.name for c in self._columns]
        rows_txt = [row_to_texts(r) for r in self._rows]
        widths = compute_column_widths(headers, rows_txt)

        sep = make_separator(widths)
        lines = [sep, make_data_line(headers, widths), sep]
        for r in rows_txt:
            lines.append(make_data_line(r, widths))
        lines.append(sep)

        return "\n".join(lines)

    def _validate_join_columns(self, other: 'Table', other_foreign_key: Sequence[str]) -> None:
        """
        Internal helper to validate that a join operation is logically sound.
        
        Checks that the foreign key matches the primary key in length and data types.
        """
        if len(other_foreign_key) != len(self._primary_key):
            raise ValueError("FK length must match PK length.")

        for self_pk_name, other_fk_name in zip(self._primary_key, other_foreign_key):
            s_col = self._column_map[self_pk_name]
            o_col = other._column_map[other_fk_name]
            if s_col.column_type.data_type != o_col.column_type.data_type:
                raise TypeError(f"Type mismatch: {s_col.column_type.data_type} vs {o_col.column_type.data_type}")

    def _create_join_result_table(self, other: 'Table') -> 'Table':
        """
        Internal helper to construct the empty result table for a join.
        
        Generates prefixed column names (table.column) and a combined primary key.
        """
        res_name = f"{self.name}_{other.name}"
        res_cols = self._prefixed_columns(self.name) + other._prefixed_columns(other.name)
        res_pk = self._prefixed_primary_key(self.name) + other._prefixed_primary_key(other.name)
        return Table(name=res_name, columns=res_cols, primary_key=res_pk)

    def _prefixed_columns(self, table_name: str) -> list[Column]:
        """Returns columns with names prefixed by the table name."""
        return [Column(f"{table_name}.{c.name}", ColumnType(c.column_type.data_type, c.column_type.not_null, False)) for c in self._columns]

    def _prefixed_primary_key(self, table_name: str) -> list[str]:
        """Returns primary key names prefixed by the table name."""
        return [f"{table_name}.{pk}" for pk in self._primary_key]

    def _build_primary_key_lookup(self) -> dict[Row, Row]:
        """Creates a dictionary mapping PK values to the entire row for fast joining."""
        pk_idxs = self._indexes_for(self._primary_key)
        return {self._extract_key(r, pk_idxs): r for r in self._rows}

    def _row_to_mapping(self, row: Row) -> Mapping[str, Value]:
        """Converts a row tuple into a dict keyed by column names."""
        return {c.name: v for c, v in zip(self._columns, row)}

    def where(self, predicate: Callable[[Mapping[str, Value]], bool]) -> 'Table':
        """
        Filter rows based on a condition function.
        
        Args:
            predicate: A function that takes a dict (column: value) and returns bool.
            
        Returns:
            Table: A new table containing only matching rows.
        """
        res = Table(self.name, self._columns, self._primary_key)
        for r in self._rows:
            if predicate(self._row_to_mapping(r)):
                res._rows.append(r)
        return res

    def get_column(self, column_name: str) -> Sequence[Value]:
        """
        Extract all values for a specific column as a sequence.
        
        Args:
            column_name (str): The name of the column.
            
        Returns:
            Sequence[Value]: All values in that column across all rows.
        """
        idx = self._column_index[column_name]
        return [r[idx] for r in self._rows]

    def test_prefix(self, column_name: str, prefix: str) -> None:
        """
        Přidá do tabulky nový sloupec se jménem prefix_ok, který obsahuje
        hodnotu 1, pokud daný textový sloupec začíná určitým prefixem,
        jinak 0. Hodnota NULL se považuje za řetězec, který prefixu nevyhovuje.
        """
        if column_name not in self._column_map.keys():
            raise ValueError(f"Column {column_name} not found in table {self.name}")
        
        check_values = self.get_column(column_name)
        # Přidání nového sloupce
        novy_sloupec = Column("prefix_ok", ColumnType(DataType.INT))
        self._columns.append(novy_sloupec)
        self._column_map[novy_sloupec.name] = novy_sloupec
        self._column_index[novy_sloupec.name] = len(self._columns) - 1
        
        for idx, value in enumerate(check_values):
            if value is None:
                prefix_ok = 0
            elif not value.startswith(prefix):
                prefix_ok = 0
            else:
                prefix_ok = 1
            self._rows[idx] = self._rows[idx] + (prefix_ok, )
            
    def atomic_add(self, other: 'Table') -> None:
        """
        Očekává jinou tabulku a přidá její obsah na konec tabulky self.
        Zajišťuje atomicitu (přidá buď všechny řádky, nebo žádný, pokud dojde k chybě).
        V případě nekompatibilních tabulek vyvolá výjimku ValueError.
        """
        

def count_null(table: Table, columns: list[str]) -> dict[str, int]:
    """
    Spočítá počet hodnot NULL (None) v určených sloupcích tabulky
    a vrátí slovník mapující jméno sloupce na počet hodnot NULL v tomto sloupci.
    """
    
    column_names = [column.name for column in table.columns]
    for column in columns:
        if column not in column_names:
            raise ValueError(f"Column {column_name} not found in table {self.name}")
        
        col_values =  table.get_column(column)
        for value in col_values:
            if value is None:
                null_count[column] += 1
        

