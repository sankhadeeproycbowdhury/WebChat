from cs50 import SQL
db = SQL("sqlite:///chat.db")


name = db.execute("SELECT username FROM info WHERE rname = ? AND username = ? AND user_id=?",
                          "sas", "roy(creator)",4 )

if len(name)>=1:
    print(name)
else:
    print("Geelo")