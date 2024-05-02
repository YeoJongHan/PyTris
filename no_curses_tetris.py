import time, random, os, msvcrt, threading, signal
from copy import deepcopy

KEY_MAPPINGS = {"H": "Up",
				"K": "Left",
				"P": "Down",
				"M": "Right"}

BLOCKS = [
	[[1],
  	[1],
	[1],
	[1]],

	[[1, 1],
  	[1, 1]],
	  
	[[0, 1],
	[1, 1],
	[1, 0]],

	[[1, 0],
  	[1, 1],
	[0, 1]],

	[[1, 0],
  	[1, 0],
	[1, 1]],

	[[0, 1],
  	[0, 1],
	[1, 1]],

	[[0, 1, 0],
  	[1, 1, 1]]

]

NUM_OF_BLOCK_TYPES = len(BLOCKS)

SQUARE, EMPTY_BLOCK = "██", "  "
RIGHT_WALL, LEFT_WALL = "", ""
LEFT_MID_WALL, RIGHT_MID_WALL, TOP_MID_WALL, BOTTOM_MID_WALL, MID_WALL = "┣", "┫", "┳", "┻", "╋"
TOP_LEFT_WALL, TOP_RIGHT_WALL, BOTTOM_LEFT_WALL, BOTTOM_RIGHT_WALL = "┏", "┓", "┗", "┛"
HORIZONTAL_WALL, VERTICAL_WALL = "━", "┃"

SCOREBOARD_WIDTH, SCOREBOARD_HEIGHT = 8,1
GAME_BOARD_WIDTH, GAME_BOARD_HEIGHT = 10, 20
RIGHT_MENU_WIDTH, RIGHT_MENU_HEIGHT = 5, 8
BOARD_HEIGHT = 25
GAME_BOARD_OFFSET = SCOREBOARD_WIDTH + 2 * 2

START_X, START_Y = 5, 0

class Board:
	def __init__(self):
		self.score = 0
		rows = [0] * GAME_BOARD_WIDTH
		self.blocks = [rows.copy() for _ in range(GAME_BOARD_HEIGHT)]
		self.current_block = Block(START_X, START_Y)

	def game_over(self):
		global LISTENING
		self.score = 0
		print("Game Over!")
		LISTENING = 0
		exit()
	
	def start_game(self):
		while True:
			if self.is_gameover():
				break
			self.update_board()
			self.current_block = Block(START_X, START_Y)
		self.game_over()

	def increase_score(self):
		return

	def is_gameover(self):
		block = self.current_block.return_block()
		block_height = len(block)
		
		for height in range(block_height):
			for width in range(len(block[0])):
				if block[height][width] and self.blocks[START_Y + height][START_X + width]:
					return True
		return  False

	def check_collision(self, new_x, new_y):
		block = self.current_block.return_block()
		block_height = len(block)
		blocks_copy = deepcopy(self.blocks)
	
		for width in range(len(block[0])):
			for height in range(block_height):
				if block[height][width] == 1:
					blocks_copy[self.current_block.get_y() + height][self.current_block.get_x() + width] = 0

		for width in range(len(block[0])):
			for height in range(block_height):
				if blocks_copy[new_y + height][new_x + width] == 1 and block[height][width] == 1:
					return True
		return False

	def update_board(self):
		self.insert_block_into_board(self.current_block.get_x(), self.current_block.get_y())
		while True:
			time.sleep(0.2)
			# os.system("cls")
			self.print_board()

			try:
				if self.check_collision(self.current_block.get_x(), self.current_block.get_y() + 1):
					break
			except Exception as e:
				break
			self.remove_old_block()
			self.current_block.update_y(self.current_block.get_y() + 1)
			self.shift_block(self.current_block.get_x(), self.current_block.get_y())

	def remove_old_block(self):
		old_x, old_y = self.current_block.get_x(), self.current_block.get_y()
		block = self.current_block.return_block()
		block_height = len(block)
		for width in range(len(block[0])):
			for height in range(block_height):
				self.blocks[old_y + height][old_x + width] = 0

	def insert_block_into_board(self, x, y):
		block = self.current_block.return_block()
		block_height = len(block)

		for height in range(block_height):
			for width in range(len(block[0])):
					if block[height][width]:
						self.blocks[y + height][x + width] = 1

	def shift_block(self, new_x, new_y):
		self.insert_block_into_board(new_x, new_y)

	def change_position(self, is_right):
		self.remove_old_block()
		if is_right:
			try:
				if not self.check_collision(self.current_block.get_x() + 1, self.current_block.get_y()):
					self.current_block.update_x(self.current_block.get_x() + 1)
			except Exception as e:
				return
		else:
			try:
				if not self.check_collision(self.current_block.get_x() - 1, self.current_block.get_y()):
					self.current_block.update_x(self.current_block.get_x() - 1)
			except Exception as e:
				return

	def rotate_block(self):
		self.remove_old_block()
		self.current_block.rotate_clockwise()

	def clear_line(self):
		return

	def print_board(self):
		res = self.merge_boards(self.create_scoreboard(), self.create_main_board())
		res = self.merge_boards(res, self.create_right_menu())
		print(res)

	def merge_boards(self, board1, board2):
		board1_lines = board1.split('\n')
		board2_lines = board2.split('\n')

		assert len(board1_lines) == len(board2_lines)
		new_board = ""
		for y in range(len(board1_lines)):
			new_board += board1_lines[y]
			new_board += board2_lines[y]
			new_board += '\n'
		return new_board[:-1]

	def pad_board_vertical(self, board, width):
		board_height = len(board.split('\n'))
		for _ in range(BOARD_HEIGHT - board_height):
			board += ' ' * (width * 2 + 2) + '\n'
		return board

	def create_right_menu(self):
		board = TOP_LEFT_WALL + (HORIZONTAL_WALL * 2) * RIGHT_MENU_WIDTH * 2 + TOP_RIGHT_WALL + '\n'
		for _ in range(RIGHT_MENU_HEIGHT):
			board += VERTICAL_WALL + EMPTY_BLOCK * RIGHT_MENU_WIDTH * 2 + VERTICAL_WALL + '\n'
		board += BOTTOM_LEFT_WALL + (HORIZONTAL_WALL * 2) * RIGHT_MENU_WIDTH * 2 + BOTTOM_RIGHT_WALL + '\n'
		board = self.pad_board_vertical(board, RIGHT_MENU_WIDTH * 2)
		return board

	def create_main_board(self):
		board = TOP_LEFT_WALL + (HORIZONTAL_WALL * 2) * GAME_BOARD_WIDTH + TOP_RIGHT_WALL + '\n'
		for y in range(GAME_BOARD_HEIGHT):
			board += VERTICAL_WALL + ''.join([SQUARE if x else EMPTY_BLOCK for x in self.blocks[y]]) + VERTICAL_WALL + '\n'
		board += BOTTOM_LEFT_WALL + (HORIZONTAL_WALL * 2) * GAME_BOARD_WIDTH + BOTTOM_RIGHT_WALL + '\n'
		board = self.pad_board_vertical(board, GAME_BOARD_WIDTH)
		return board

	def create_scoreboard(self):
		board = TOP_LEFT_WALL + (HORIZONTAL_WALL * 2) * SCOREBOARD_WIDTH + TOP_RIGHT_WALL + '\n'
		score_text = f"SCORE: {self.score}"
		padding = SCOREBOARD_WIDTH * 2 - len(score_text)
		for _ in range(SCOREBOARD_HEIGHT):
			board += VERTICAL_WALL + score_text + " " * padding + VERTICAL_WALL + '\n'
		board += BOTTOM_LEFT_WALL + (HORIZONTAL_WALL * 2) * SCOREBOARD_WIDTH + BOTTOM_RIGHT_WALL + '\n'
		board = self.pad_board_vertical(board, SCOREBOARD_WIDTH)
		return board

	def get_self_blocks(self):
		return self.blocks
	
	def get_current_blocks(self):
		return self.current_block


class Block:
	def __init__(self, x, y):
		self.block_type = random.randint(0, NUM_OF_BLOCK_TYPES - 1)
		self.block = BLOCKS[self.block_type]
		self.height = len(self.block)
		self.width = len(self.block[0])
		self.x = x
		self.y = y

	def create_nblock(self, given_block):
		new_block = []
		for block in given_block:
			b = []
			for is_block in block:
				if is_block:
					b.append(SQUARE)
				else:
					b.append(EMPTY_BLOCK)
			new_block.append(b)		
		return '\n'.join([''.join(block) for block in new_block])

	def rotate_anticlockwise(self):
		self.block = [[self.block[j][i] for j in range(len(self.block))] for i in range(len(self.block[0]) - 1, -1, -1)]

	def rotate_clockwise(self):
		for _ in range(3):
			self.rotate_anticlockwise()

	def return_block(self):
		return self.block	
	def get_x(self):
		return self.x

	def get_y(self):
		return self.y

	def get_height(self):
		return self.height

	def get_width(self):
		return self.width

	def update_x(self,x):
		self.x = x

	def update_y(self, y):
		self.y = y


BOARD = Board()
LISTENING = 1


def key_listener():
	global BOARD
	global LISTENING
	while LISTENING:
		key = msvcrt.getch()
		if key == b'\xe0':
			key = msvcrt.getch()
			if key.decode() in KEY_MAPPINGS:
				if BOARD is not None:
					if KEY_MAPPINGS[key.decode()] == "Up":
						BOARD.rotate_block()
					elif KEY_MAPPINGS[key.decode()] == "Left":
						BOARD.change_position(0)
					elif KEY_MAPPINGS[key.decode()] == "Right":
						BOARD.change_position(1)


def signal_handler(sig, frame):
	global LISTENING
	print("Exiting")
	LISTENING = 0
	exit()

def main():
	global BOARD
	signal.signal(signal.SIGINT, signal_handler)
	proc = threading.Thread(target=key_listener)
	proc.start()
	
	BOARD.start_game()

if __name__=="__main__":
	main()
