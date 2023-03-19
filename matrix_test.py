import matrix_wrapper
from dotenv import dotenv_values

config = dotenv_values(".env")
matrix_dest=config["matrix_dest"]
matrix_wrapper.send(matrix_dest,"test")
matrix_wrapper.receive(matrix_dest)
