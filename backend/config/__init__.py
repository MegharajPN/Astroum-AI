import pymysql

# Use PyMySQL as the MySQL driver so no C compiler is needed on Windows.
pymysql.install_as_MySQLdb()
