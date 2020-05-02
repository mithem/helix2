import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import markdown

import base


class HelixNewsletterGUI(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        global subject
        global content
        subject = tk.StringVar()
        content = tk.StringVar()
        tk.Label(self, text="Subject").pack()
        tk.Entry(self, textvariable=subject).pack()
        tk.Label(self, text="").pack()
        tk.Label(
            self, text="Markdown will automatically be converted to html.").pack()
        tk.Label(self, text="Content").pack()
        tk.Entry(self, textvariable=content).pack()
        tk.Label(text="Only show users subscribed to newsletters").pack()
        self.t_btn = tk.Button(
            text="True", command=self.toggleNewsletterOnlyBtn)
        self.t_btn.pack()
        self.users_list = tk.Listbox(self, selectmode="multiple")
        self.users_list.pack()
        self.refresh_users()
        tk.Button(self, text="Send newsletter",
                  command=self.send_newsletter).pack()

    def refresh_users(self):
        newsletter_only = self.t_btn.config("text")[-1] == "True"
        self.users_list.delete(0, "end")
        for user in base.get_all_users(newsletter_only):
            self.users_list.insert(user["id"], user["email"])

    def toggleNewsletterOnlyBtn(self):
        if self.t_btn.config('text')[-1] == 'True':
            self.t_btn.config(text='False')
        else:
            self.t_btn.config(text='True')
        self.refresh_users()

    def send_newsletter(self):
        addressees = []
        for index in self.users_list.curselection():
            email = (self.users_list.get(index))
            user = base.get_user_by_email(email)
            addressees.append(user)
        html = markdown.markdown(content.get())
        print(html)
        newsletter = base.mailservice.Newsletter(
            False, html, subject.get(), addressees)
        base.mailservice.send_newsletter(newsletter)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Helix Newsletter GUI")
    gui = HelixNewsletterGUI(root)
    gui.mainloop()
