import sqlite3
import tkinter as tk
from tkinter import ttk

# Connect to existing database
conn = sqlite3.connect("smartattend.db")

root = tk.Tk()
root.title("SmartAttend - Database Viewer")
root.geometry("1100x600")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)


def show_table(table_name):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=table_name.capitalize())

    cursor = conn.execute(f"SELECT * FROM {table_name}")

    columns = [desc[0] for desc in cursor.description]

    tree = ttk.Treeview(frame, columns=columns, show="headings")

    for col in columns:
        tree.heading(col, text=col.upper())
        tree.column(col, width=150)

    scrollbar = ttk.Scrollbar(
        frame, orient="horizontal", command=tree.xview
    )
    tree.configure(xscrollcommand=scrollbar.set)

    tree.pack(fill="both", expand=True)
    scrollbar.pack(fill="x")

    for row in cursor.fetchall():
        tree.insert("", "end", values=row)


show_table("students")
show_table("attendance")

root.mainloop()

conn.close()