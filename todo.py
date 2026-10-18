import json
import os
import sys

TASKS_FILE = "tasks.json"


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        if isinstance(tasks, list):
            return tasks
    except (json.JSONDecodeError, OSError):
        pass
    print(f"Warning: {TASKS_FILE} is invalid, starting with an empty list.", file=sys.stderr)
    return []


def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def parse_index(arg, tasks):
    try:
        n = int(arg)
    except ValueError:
        print(f"Error: '{arg}' is not a valid number.", file=sys.stderr)
        sys.exit(1)
    if n < 1 or n > len(tasks):
        print(f"Error: no task at position {n}.", file=sys.stderr)
        sys.exit(1)
    return n - 1


def cmd_add(tasks, args):
    if len(args) != 1:
        print('Error: usage: add "task"', file=sys.stderr)
        sys.exit(1)
    tasks.append({"task": args[0], "done": False})
    save_tasks(tasks)
    print(f"Added: {args[0]}")


def cmd_list(tasks, args):
    if args:
        print("Error: usage: list", file=sys.stderr)
        sys.exit(1)
    if not tasks:
        print("No tasks.")
        return
    for i, t in enumerate(tasks, 1):
        mark = "x" if t.get("done") else " "
        print(f"{i}. [{mark}] {t.get('task', '')}")


def cmd_done(tasks, args):
    if len(args) != 1:
        print("Error: usage: done <number>", file=sys.stderr)
        sys.exit(1)
    i = parse_index(args[0], tasks)
    tasks[i]["done"] = True
    save_tasks(tasks)
    print(f"Done: {tasks[i]['task']}")


def cmd_delete(tasks, args):
    if len(args) != 1:
        print("Error: usage: delete <number>", file=sys.stderr)
        sys.exit(1)
    i = parse_index(args[0], tasks)
    removed = tasks.pop(i)
    save_tasks(tasks)
    print(f"Deleted: {removed['task']}")


def launch_gui():
    import tkinter as tk
    from tkinter import messagebox, ttk

    tasks = load_tasks()

    root = tk.Tk()
    root.title("Todo")
    root.geometry("520x420")
    root.minsize(400, 300)

    style = ttk.Style(root)
    style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    top = ttk.Frame(root, padding=10)
    top.pack(fill="x")

    entry = ttk.Entry(top)
    entry.pack(side="left", fill="x", expand=True)

    add_btn = ttk.Button(top, text="Add", command=lambda: add_task())
    add_btn.pack(side="left", padx=(8, 0))

    body = ttk.Frame(root, padding=(10, 0, 10, 0))
    body.pack(fill="both", expand=True)

    tree = ttk.Treeview(
        body, columns=("num", "status", "task"), show="headings", selectmode="browse"
    )
    tree.heading("num", text="#")
    tree.heading("status", text="Done")
    tree.heading("task", text="Task")
    tree.column("num", width=40, anchor="center", stretch=False)
    tree.column("status", width=60, anchor="center", stretch=False)
    tree.column("task", width=340)
    scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    tree.tag_configure("done", foreground="#999999")

    actions = ttk.Frame(root, padding=10)
    actions.pack(fill="x")

    done_btn = ttk.Button(actions, text="Toggle done", command=lambda: toggle_done())
    done_btn.pack(side="left")
    delete_btn = ttk.Button(actions, text="Delete", command=lambda: delete_task())
    delete_btn.pack(side="left", padx=(8, 0))
    clear_btn = ttk.Button(actions, text="Clear done", command=lambda: clear_done())
    clear_btn.pack(side="left", padx=(8, 0))

    status_var = tk.StringVar()
    status = ttk.Label(actions, textvariable=status_var, anchor="e")
    status.pack(side="right", fill="x", expand=True)

    def refresh(selected=None):
        tree.delete(*tree.get_children())
        done_count = 0
        for i, t in enumerate(tasks, 1):
            is_done = bool(t.get("done"))
            done_count += is_done
            tree.insert(
                "",
                "end",
                iid=str(i - 1),
                values=(i, "x" if is_done else " ", t.get("task", "")),
                tags=("done",) if is_done else (),
            )
        status_var.set(
            f"{len(tasks)} task(s) - {len(tasks) - done_count} open, {done_count} done"
        )
        if selected is not None and tree.exists(str(selected)):
            tree.selection_set(str(selected))
            tree.see(str(selected))

    def selected_index():
        sel = tree.selection()
        return int(sel[0]) if sel else None

    def warn_no_selection():
        messagebox.showinfo("Todo", "Select a task first.", parent=root)

    def add_task():
        text = entry.get().strip()
        if not text:
            root.bell()
            return
        tasks.append({"task": text, "done": False})
        save_tasks(tasks)
        entry.delete(0, "end")
        refresh(len(tasks) - 1)
        entry.focus_set()

    def toggle_done():
        i = selected_index()
        if i is None:
            warn_no_selection()
            return
        tasks[i]["done"] = not tasks[i].get("done", False)
        save_tasks(tasks)
        refresh(i)

    def delete_task():
        i = selected_index()
        if i is None:
            warn_no_selection()
            return
        if not messagebox.askyesno("Delete", f"Delete: {tasks[i]['task']}?", parent=root):
            return
        tasks.pop(i)
        save_tasks(tasks)
        refresh(min(i, len(tasks) - 1) if tasks else None)

    def clear_done():
        remaining = [t for t in tasks if not t.get("done")]
        removed = len(tasks) - len(remaining)
        if not removed:
            messagebox.showinfo("Todo", "No completed tasks.", parent=root)
            return
        if not messagebox.askyesno(
            "Clear done", f"Delete {removed} completed task(s)?", parent=root
        ):
            return
        tasks[:] = remaining
        save_tasks(tasks)
        refresh()

    def on_double_click(_event):
        toggle_done()

    entry.bind("<Return>", lambda _e: add_task())
    tree.bind("<Double-1>", on_double_click)
    tree.bind("<Delete>", lambda _e: delete_task())

    refresh()
    entry.focus_set()
    root.mainloop()


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "delete": cmd_delete,
}


def main():
    if not len(sys.argv) > 1:
        launch_gui()
        return
    if sys.argv[1] not in COMMANDS:
        print("Usage: todo.py [add|list|done|delete] [args]", file=sys.stderr)
        print("  (no arguments)  Open the GUI", file=sys.stderr)
        print('  add "task"    Add a new task', file=sys.stderr)
        print("  list          List all tasks", file=sys.stderr)
        print("  done <n>      Mark task n as done", file=sys.stderr)
        print("  delete <n>    Delete task n", file=sys.stderr)
        sys.exit(1)
    command = sys.argv[1]
    tasks = load_tasks()
    COMMANDS[command](tasks, sys.argv[2:])


if __name__ == "__main__":
    main()
