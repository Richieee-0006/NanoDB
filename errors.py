from decimal import Decimal
from nanodb import Table, Column, ColumnType, DataType


def test_errors() -> None:
    """
    Demonstrate the relational integrity enforcement of the NanoDB engine.
    
    This function intentionally attempts various invalid operations to show 
    how the Table class raises appropriate exceptions (ValueError, TypeError)
    when constraints are violated.
    """
    
    # 1. Setup a standard table with constraints.
    person = Table(
        "person",
        [
            Column("id", ColumnType(DataType.INT, not_null=True, unique=True)),
            Column("name", ColumnType(DataType.TEXT, not_null=True)),
            Column("salary", ColumnType(DataType.DECIMAL)),
        ],
        primary_key=("id",),
    )

    # 2. Add a valid row.
    person.insert(("id", "name", "salary"), (1, "Alice", Decimal("10.50")))

    print("--- Testing Constraint Violations ---")

    # 3. Test: Primary Key Uniqueness
    try:
        # Attempting to insert another person with ID 1.
        person.insert(("id", "name"), (1, "Bob"))
    except ValueError as exc:
        print(f"EXPECTED ERROR (Duplicate PK): {exc}")

    # 4. Test: NOT NULL Constraint
    try:
        # Attempting to insert a row where 'name' (NOT NULL) is None.
        person.insert(("id", "name"), (2, None))
    except ValueError as exc:
        print(f"EXPECTED ERROR (NOT NULL): {exc}")

    # 5. Test: Data Type Safety
    try:
        # Attempting to insert a float into a DECIMAL column.
        # NanoDB is strict and requires the exact type (Decimal).
        person.insert(("id", "name", "salary"), (3, "Cyril", 10.5))
    except TypeError as exc:
        print(f"EXPECTED ERROR (Invalid Type): {exc}")

    # 6. Test: Schema Integrity
    try:
        # Attempting to insert into a column that does not exist.
        person.insert(("unknown_column",), (123,))
    except ValueError as exc:
        print(f"EXPECTED ERROR (Unknown Column): {exc}")

    print("\nError testing complete.")


if __name__ == "__main__":
    test_errors()
