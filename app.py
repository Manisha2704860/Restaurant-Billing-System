import tkinter as tk
from ui.main_ui import LoginPage

def main():
    root = tk.Tk()
    LoginPage(root)
    root.mainloop()

if __name__ == "__main__":
    main()
