from typing import Callable, Sequence

from nanodb import Mapping, Row, Table, Value


class MyTable(Table):
    """
    An extension of the base Table class providing advanced data manipulation features.
    
    MyTable adds capabilities such as creating projection views (Materialized Views),
    sorting data based on custom predicates, and performing conditional row deletions.
    """

    def materializedView(
        self,
        column_names: Sequence[str],
    ) -> Table:
        """
        Create a new table containing a subset of the original table's columns.
        
        The resulting "view" table contains all the rows from the original table,
        but only for the specified columns. It automatically preserves the 
        original table's primary key columns to ensure relational integrity 
        in the resulting view.
        
        Args:
            column_names (Sequence[str]): The subset of column names to include.
            
        Returns:
            Table: A new Table instance containing the projected data.
        """
        # 1. Identify which columns to include (user requested + primary key).
        pk_set = set(self.primary_key)
        requested_set = set(column_names)
        
        # Merge sets to ensure PK is always included.
        final_column_names = []
        for col in self.columns:
            if col.name in requested_set or col.name in pk_set:
                final_column_names.append(col.name)
        
        # 2. Define the schema for the new table.
        new_columns = [self._column_map[name] for name in final_column_names]
        view_table = Table(f"view_{self.name}", new_columns, self.primary_key)
        
        # 3. Populate the new table with projected data.
        # We use a set of indices to extract only the relevant parts of each row tuple.
        indices = self._indexes_for(final_column_names)
        for row in self._rows:
            projected_values = self._extract_key(row, indices)
            view_table.insert(final_column_names, projected_values)
            
        return view_table

    def orderBy(
        self,
        lt: Callable[[Row, Row], bool],
    ) -> Table:
        """
        Create a new table with the same schema and data, but sorted.
        
        The sorting is performed using a custom "less-than" predicate function.
        
        Args:
            lt (Callable[[Row, Row], bool]): A function that takes two rows and 
                                             returns True if the first is "less than" 
                                             the second.
                                             
        Returns:
            Table: A new Table instance with sorted rows.
        """
        # 1. Create a copy of the current table structure.
        sorted_table = Table(f"sorted_{self.name}", self._columns, self.primary_key)
        
        # 2. Perform the sort on the internal row list.
        # We convert the 'lt' predicate into a key-compatible comparison if needed, 
        # or use a wrapper. Here we'll use functools.cmp_to_key for compatibility.
        from functools import cmp_to_key
        
        def comparator(a, b):
            if lt(a, b): return -1
            if lt(b, a): return 1
            return 0
            
        sorted_rows = sorted(self._rows, key=cmp_to_key(comparator))
        
        # 3. Inject the sorted rows into the new table.
        # Note: We bypass 'insert' to avoid redundant validation since data is already validated.
        sorted_table._rows = sorted_rows
        
        return sorted_table

    def delete(self, where_cond: Callable[[Mapping[str, Value]], bool]) -> None:
        """
        Remove all rows from the table that satisfy a given condition.
        
        This operation modifies the table in-place.
        
        Args:
            where_cond (Callable[[Mapping[str, Value]], bool]): A predicate function 
                that receives a row mapping (dict) and returns True for rows 
                that should be deleted.
        """
        # We iterate backwards or use filtering to avoid index issues during deletion.
        # Here, we reconstruct the row list by keeping only those that DON'T match.
        self._rows = [
            row for row in self._rows 
            if not where_cond(self._row_to_mapping(row))
        ]


if __name__ == "__main__":
    # Internal demonstration of MyTable features.
    from nanodb import Column, ColumnType, DataType
    
    # Setup sample table.
    t = MyTable(
        "test",
        [
            Column("id", ColumnType(DataType.INT, not_null=True, unique=True)),
            Column("val", ColumnType(DataType.TEXT))
        ],
        primary_key=["id"]
    )
    
    t.insert(["id", "val"], (2, "B"))
    t.insert(["id", "val"], (1, "A"))
    
    print("Original Table:")
    print(t.to_text())
    
    # Test Sorting (by ID).
    sorted_t = t.orderBy(lambda a, b: a[0] < b[0])
    print("\nSorted Table (by ID):")
    print(sorted_t.to_text())
    
    # Test Deletion.
    t.delete(lambda row: row["val"] == "B")
    print("\nTable after deleting 'B':")
    print(t.to_text())
