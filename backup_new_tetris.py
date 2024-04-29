import time
import random
import os
import msvcrt
import threading
import signal
import curses
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

SCOREBOARD_WIDTH, SCOREBOARD_HEIGHT = 18 + 2, 1 + 2
GAME_BOARD_WIDTH, GAME_BOARD_HEIGHT = 20 + 2, 20 + 2
GAME_WIDTH, GAME_HEIGHT = 10, 20
RIGHT_MENU_WIDTH, RIGHT_MENU_HEIGHT = 20 + 2, 8 + 2
BOARD_HEIGHT = 25
GAME_BOARD_OFFSET = SCOREBOARD_WIDTH
RIGHT_MENU_OFFSET = GAME_BOARD_OFFSET + GAME_BOARD_WIDTH

START_X, START_Y = 5, 0

class Board:
    def __init__(self):
        self.score = 0
        rows = [0] * GAME_WIDTH
        self.blocks = [rows.copy() for _ in range(GAME_HEIGHT)]
        self.current_block = None
        self.stdscr = curses.initscr()
        self.scoreboard_menu = self.stdscr.subwin(SCOREBOARD_HEIGHT, SCOREBOARD_WIDTH, 0, 0)
        self.main_board = self.stdscr.subwin(GAME_BOARD_HEIGHT, GAME_BOARD_WIDTH, 0, GAME_BOARD_OFFSET)
        self.right_menu = self.stdscr.subwin(RIGHT_MENU_HEIGHT, RIGHT_MENU_WIDTH, 0, RIGHT_MENU_OFFSET)
        
        curses.noecho()
        self.stdscr.keypad(True)
        self.stdscr.nodelay(1)
        curses.curs_set(0)

        self.gravity_proc = None
        self.timing = 0.5
        self.lines_cleared = 0

    def game_over(self):
        global GAME_RUNNING
        self.score = 0
        GAME_RUNNING = 0
        self.stdscr.addstr("Game Over! (Ctrl+C)")
        curses.endwin()

    def start_game(self):
        self.create_all_boards()
        self.get_new_block()

        self.update_board()
        self.game_over()

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

    def block_gravity(self):
        global GAME_RUNNING
        while GAME_RUNNING:
            time.sleep(self.timing)
            try:
                if self.check_collision(self.current_block.get_x(), self.current_block.get_y() + 1):
                    if self.is_gameover():
                        self.game_over()
                    break
            except Exception as e:
                if self.is_gameover():
                    self.game_over()
                break
            self.shift_block(self.current_block.get_x(), self.current_block.get_y() + 1)
        self.check_lines()
        self.get_new_block()

    def get_new_block(self):
        self.current_block = Block(START_X, START_Y)
        self.insert_block_into_board(self.current_block.get_x(), self.current_block.get_y()) 
        self.gravity_proc = threading.Thread(target=self.block_gravity)
        self.gravity_proc.start()

    def update_board(self):
        while True:
            self.update_main_board()
            key = self.stdscr.getch()
            if key == curses.KEY_LEFT:
                self.change_position(is_right=0)
            elif key == curses.KEY_RIGHT:
                self.change_position(is_right=1)
            elif key == curses.KEY_UP:
                self.rotate_clockwise()
            elif key == ord(' '):
                self.hard_drop()
            elif key == ord('z'):
                self.rotate_anticlockwise()
            self.stdscr.refresh()

    def remove_old_block(self, blocks_supplied=None):
        if blocks_supplied is None:
            blocks_supplied = self.blocks
        old_x, old_y = self.current_block.get_x(), self.current_block.get_y()
        block = self.current_block.return_block()
        block_height = len(block)
        for width in range(len(block[0])):
            for height in range(block_height):
                if block[height][width]:
                    blocks_supplied[old_y + height][old_x + width] = 0
                    self.main_board.addstr(old_y + height + 1, (old_x + width)*2 + 1, EMPTY_BLOCK)
        self.main_board.refresh()

    def insert_block_into_board(self, x, y):
        block = self.current_block.return_block()
        block_height = len(block)

        for height in range(block_height):
            for width in range(len(block[0])):
                    if block[height][width]:
                        self.blocks[y + height][x + width] = 1

    def shift_block(self, new_x, new_y):
        self.remove_old_block()
        self.current_block.update_x(new_x)
        self.current_block.update_y(new_y)
        self.insert_block_into_board(self.current_block.get_x(), self.current_block.get_y())

    def change_position(self, is_right):
        self.remove_old_block()
        if is_right:
            try:
                if not self.check_collision(self.current_block.get_x() + 1, self.current_block.get_y()):
                    self.current_block.update_x(self.current_block.get_x() + 1  )
            except Exception as e:
                return
        else:
            try:
                if not self.check_collision(self.current_block.get_x() - 1, self.current_block.get_y()) and\
                not self.current_block.get_x() == 0:
                    self.current_block.update_x(self.current_block.get_x() - 1)
            except Exception as e:
                return

    def rotate_clockwise(self):
        self.remove_old_block()
        self.current_block.rotate_clockwise()
    
    def rotate_anticlockwise(self):
        self.remove_old_block()
        self.current_block.rotate_anticlockwise()

    def check_lines(self):
        lines = []
        for line_num in range(len(self.blocks)):
             if len(self.blocks[line_num]) == sum(self.blocks[line_num]):
                lines.append(line_num)
        if len(lines) != 0:
            self.clear_lines(lines)

    def clear_lines(self, lines):
        multiplier = len(lines)
        for line in lines:
            self.blocks.pop(line)
            self.blocks.insert(0, [0] * GAME_WIDTH)
        self.score += 10 * multiplier
        self.lines_cleared += len(lines)
        if (self.lines_cleared + 1) % 11 == 0:
             self.timing /= 1.2
        self.update_score()
        self.update_main_board()

    # Game features
    def hard_drop(self):
        current_y = self.current_block.get_y()
        i = 0
        while i < len(self.blocks):
            try:
                if self.check_collision(self.current_block.get_x(), current_y + i):
                    break
            except:
                break
            i += 1
        self.shift_block(self.current_block.get_x(), self.current_block.get_y() + i -1)

    # Board and menu updates/creations 
    def update_score(self):
        self.scoreboard_menu.addstr(1, 1, f"Score: {self.score}")
        self.scoreboard_menu.refresh()
    
    def update_main_board(self):
        for y in range(len(self.blocks)):
            self.main_board.addstr(y + 1, 1, ''.join([SQUARE if x else EMPTY_BLOCK for x in self.blocks[y]]))
        # for y in range(len(self.blocks)):
        #     for x in range(len(self.blocks[0])):
        #         if self.blocks[y][x]: self.main_board.addstr(y + 1, x*2 + 1, SQUARE)
        self.main_board.refresh()

    def create_all_boards(self):
        self.create_scoreboard()
        self.create_main_board()
        self.create_right_menu()
        self.scoreboard_menu.addstr(1, 1, f"Score: {self.score}")

    def create_right_menu(self):
        self.right_menu.box()

    def create_main_board(self):
        self.main_board.box()

    def create_scoreboard(self):
        self.scoreboard_menu.box()

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
GAME_RUNNING = 1


def signal_handler(sig, frame):
	global GAME_RUNNING
	print("Exiting")
	GAME_RUNNING = 0
	exit()

def main():
	global BOARD
	signal.signal(signal.SIGINT, signal_handler)
	BOARD.start_game()

if __name__=="__main__":
	main()
