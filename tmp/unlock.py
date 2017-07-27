

from sqlite3 import dbapi2 as sqlite



connection = sqlite.connect('test.db')

connection.commit()

connection.close()





