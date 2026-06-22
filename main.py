from datetime import date
from decimal import Decimal
from mixins import SequenceToStringMixin
from nanodb import Column, ColumnType, DataType, Table

class TableWithRepr(Table, SequenceToStringMixin):
    """
    A Table subclass that includes the SequenceToStringMixin for better 
    debugging visibility in the console.
    """
    pass

def main() -> None:
    """
    The main entry point for the NanoDB demonstration.
    
    This script performs the following end-to-end workflow:
    1. Schema Definition: Defines 'customer' and 'order' tables with specific 
       data types and primary key constraints.
    2. Data Population: Inserts multiple rows into both tables, demonstrating 
       handling of dates, decimals, and NULL values.
    3. Relational Joins: Executes an inner join between customers and orders 
       using customer_id as the linkage.
    4. Advanced Queries: Demonstrates the 'where' method for functional filtering.
    5. Visualization: Outputs all results as formatted ASCII tables.
    """
    
    # --- 1. Define the 'customer' table ---
    # We use TableWithRepr to show off the custom __repr__ mixin.
    customer = TableWithRepr(
        "customer",
        [
            Column("id", ColumnType(DataType.INT, not_null=True, unique=True)),
            Column("name", ColumnType(DataType.TEXT, not_null=True)),
            Column("birth_date", ColumnType(DataType.DATE)),
        ],
        primary_key=("id",),
    )

    # --- 2. Define the 'order' table ---
    order_tbl = Table(
        "order",
        [
            Column("id", ColumnType(DataType.INT, not_null=True, unique=True)),
            Column("customer_id", ColumnType(DataType.INT)),
            Column("total", ColumnType(DataType.DECIMAL, not_null=True)),
            Column("created", ColumnType(DataType.DATE, not_null=True)),
        ],
        primary_key=("id",),
    )

    # --- 3. Insert Customer Data ---
    customer.insert(("id", "name", "birth_date"), (1, "Alice", date(1995, 5, 17)))
    customer.insert(("id", "name", "birth_date"), (2, "Bob", None))  # Demonstrating NULL
    customer.insert(("id", "name", "birth_date"), (3, "Cyril", date(2001, 1, 10)))

    # --- 4. Insert Order Data ---
    # Note how some orders reference customers, while others (ID 103) have no customer (NULL).
    order_tbl.insert(("id", "customer_id", "total", "created"), (100, 1, Decimal("120.50"), date(2026, 3, 1)))
    order_tbl.insert(("id", "customer_id", "total", "created"), (101, 1, Decimal("75.00"), date(2026, 3, 2)))
    order_tbl.insert(("id", "customer_id", "total", "created"), (102, 2, Decimal("33.30"), date(2026, 3, 3)))
    order_tbl.insert(("id", "customer_id", "total", "created"), (103, None, Decimal("9.99"), date(2026, 3, 4)))
    order_tbl.insert(("id", "customer_id", "total", "created"), (104, 999, Decimal("15.00"), date(2026, 3, 5))) # Orphan record

    # --- 5. Output Initial Tables ---
    print("CUSTOMER TABLE:")
    print(customer.to_text())
    print()

    print("ORDER TABLE:")
    print(order_tbl.to_text())
    print()

    # --- 6. Demonstrate Inner Join ---
    # We join customer (PK) with order (FK: customer_id).
    # This will omit order 103 (NULL FK) and order 104 (Unknown FK).
    joined = customer.inner_join(order_tbl, ("customer_id",))

    print("INNER JOIN RESULT (customer ⨝ order):")
    print(joined.to_text())
    print()

    # --- 7. Demonstrate Metadata and Iteration ---
    print(f"Summary: {len(customer)} customers, {len(order_tbl)} orders, {len(joined)} matched results.")
    print("\nFirst 3 rows of the join result (raw tuples):")
    for row in list(joined)[:3]:
        print(row)

    # --- 8. Demonstrate Functional Filtering (WHERE) ---
    print("\nFiltering for customers whose names start with 'A':")
    ac_customers = customer.where(lambda row: row["name"].startswith("A"))
    print(ac_customers.to_text())

    # --- 9. Demonstrate Mixin Representation ---
    print("\nTesting __repr__ from Mixin:")
    print(f"Order Table Repr: {repr(order_tbl)}") # Standard table (no mixin)
    print(f"Customer Table Repr: {repr(customer)}") # Mixed-in table


if __name__ == "__main__":
    main()
