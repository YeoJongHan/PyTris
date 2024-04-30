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

	[[1, 1],
  	[1, 0],
	[1, 0]],

	[[1, 1],
  	[0, 1],
	[0, 1]],

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
BLOCK_HOLD_WIDTH, BLOCK_HOLD_HEIGHT = SCOREBOARD_WIDTH, 10
INST_MENU_WIDTH, INST_MENU_HEIGHT = RIGHT_MENU_WIDTH, GAME_BOARD_HEIGHT - RIGHT_MENU_HEIGHT

BOARD_HEIGHT = 25
GAME_BOARD_OFFSET = SCOREBOARD_WIDTH
RIGHT_MENU_OFFSET = GAME_BOARD_OFFSET + GAME_BOARD_WIDTH
BLOCK_HOLD_OFFSET = SCOREBOARD_HEIGHT
INST_MENU_OFFSET_X, INST_MENU_OFFSET_Y = RIGHT_MENU_OFFSET, RIGHT_MENU_HEIGHT

START_X, START_Y = 5, 0

class Board:
    def __init__(self):
        self.score = 0
        rows = [0] * GAME_WIDTH
        self.blocks = [rows.copy() for _ in range(GAME_HEIGHT)]
        self.blocks_copy = deepcopy(self.blocks)
        self.current_block = Block(START_X, START_Y)
        self.stdscr = curses.initscr()
        self.scoreboard_menu = self.stdscr.subwin(SCOREBOARD_HEIGHT, SCOREBOARD_WIDTH, 0, 0)
        self.main_board = self.stdscr.subwin(GAME_BOARD_HEIGHT, GAME_BOARD_WIDTH, 0, GAME_BOARD_OFFSET)
        self.right_menu = self.stdscr.subwin(RIGHT_MENU_HEIGHT, RIGHT_MENU_WIDTH, 0, RIGHT_MENU_OFFSET)
        self.block_hold_menu = self.stdscr.subwin(BLOCK_HOLD_HEIGHT, BLOCK_HOLD_WIDTH, BLOCK_HOLD_OFFSET, 0)
        self.instructions_menu = self.stdscr.subwin(INST_MENU_HEIGHT, INST_MENU_WIDTH, INST_MENU_OFFSET_Y, INST_MENU_OFFSET_X)
        
        curses.noecho()
        self.stdscr.keypad(True)
        self.stdscr.nodelay(1)
        curses.curs_set(0)

        self.gravity_proc = None
        self.timing = 0.5
        self.lines_cleared = 0
        self.next_block = Block(START_X, START_Y)

        self.can_hold = 0
        self.block_held = None

    def game_over(self):
        global GAME_RUNNING
        self.score = 0
        GAME_RUNNING = 0
        self.stdscr.addstr("Game Over! (Ctrl+C)")
        curses.endwin()
        print("Game Over!")

    def start_game(self):
        global GAME_RUNNING
        GAME_RUNNING = 1
        self.create_all_boards()
        self.get_new_block()
        self.update_board()

    def is_gameover(self):
        block = self.current_block.return_block()
        block_height = len(block)
        
        for height in range(block_height):
            for width in range(len(block[0])):
                if block[height][width] and self.blocks[START_Y + height][START_X + width]:
                    return True
        return False

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
        if GAME_RUNNING:
            self.get_new_block()
            self.check_lines()

    def get_new_block(self):
        self.can_hold = 1
        self.blocks = deepcopy(self.blocks_copy)
        self.current_block = self.next_block
        self.next_block = Block(START_X, START_Y)
        self.update_next_block()
        self.insert_block_into_board(self.current_block.get_x(), self.current_block.get_y())
        self.gravity_proc = threading.Thread(target=self.block_gravity)
        self.gravity_proc.start()

    def update_board(self):
        global GAME_RUNNING
        while GAME_RUNNING:
            self.update_main_board(self.blocks_copy)
            key = self.stdscr.getch()
            if key == curses.KEY_LEFT:
                self.change_position(is_right=0)
            elif key == curses.KEY_RIGHT:
                self.change_position(is_right=1)
            elif key == curses.KEY_UP:
                self.rotate_block(clockwise=1)
            elif key == curses.KEY_DOWN:
                try:
                    if not self.check_collision(self.current_block.get_x(), self.current_block.get_y() + 1):
                        self.shift_block(self.current_block.get_x(), self.current_block.get_y() + 1)
                except:
                    pass
            elif key == ord(' '):
                self.hard_drop()
            elif key == ord('z'):
                self.rotate_block(clockwise=0)
            elif key == ord('c'):
                self.hold_block()
            self.stdscr.refresh()

    def insert_block_into_board(self, x, y):
        block = self.current_block.return_block()
        block_height = len(block)
        self.blocks_copy = deepcopy(self.blocks)

        for height in range(block_height):
            for width in range(len(block[0])):
                if block[height][width]:
                    self.blocks_copy[y + height][x + width] = 1

    def shift_block(self, new_x, new_y):
        self.current_block.update_x(new_x)
        self.current_block.update_y(new_y)
        self.insert_block_into_board(self.current_block.get_x(), self.current_block.get_y())
        self.update_main_board(self.blocks_copy)

    def change_position(self, is_right):
        if is_right:
            try:
                if not self.check_collision(self.current_block.get_x() + 1, self.current_block.get_y()):
                    self.current_block.update_x(self.current_block.get_x() + 1)
            except Exception as e:
                return
        else:
            try:
                if not self.check_collision(self.current_block.get_x() - 1, self.current_block.get_y()) and\
                not self.current_block.get_x() == 0:
                    self.current_block.update_x(self.current_block.get_x() - 1)
            except Exception as e:
                return
        self.shift_block(self.current_block.get_x(), self.current_block.get_y())

    def rotate_block(self, clockwise=0):
        try:
            if clockwise:
                self.current_block.rotate_clockwise()
            else:
                self.current_block.rotate_anticlockwise()
            self.shift_block(self.current_block.get_x(), self.current_block.get_y())
        except:
            if clockwise:
                self.current_block.rotate_anticlockwise()
            else:
                self.current_block.rotate_clockwise()
            self.shift_block(self.current_block.get_x(), self.current_block.get_y())

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
             self.timing /= 1.4
        self.blocks_copy = deepcopy(self.blocks)
        self.update_score()
        self.update_main_board(self.blocks_copy)

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
        self.shift_block(self.current_block.get_x(), self.current_block.get_y() + i - 1)
        

    def hold_block(self):
        if self.can_hold:
            if self.block_held is None:
                self.blocks_copy = deepcopy(self.blocks)
                self.update_main_board(self.blocks_copy)
                self.block_held = self.current_block
                self.get_new_block()
            else:
                self.block_held, self.current_block = self.current_block, self.block_held
            self.can_hold = 0
            self.update_hold_menu()
            self.block_held.update_x(START_X)
            self.block_held.update_y(START_Y)

    # Board and menu updates/creations
    def update_hold_menu(self):
        self.block_hold_menu.clear()
        self.block_hold_menu.box()
        self.block_hold_menu.addstr(1, 1, "Holding:")
        block = self.block_held.return_block()
        for y in range(len(block)):
            self.block_hold_menu.addstr(BLOCK_HOLD_HEIGHT//3 + y + 1, BLOCK_HOLD_WIDTH//3 + 2, ''.join([SQUARE if x else EMPTY_BLOCK for x in block[y]]))
        
        self.block_hold_menu.refresh()

    def update_score(self):
        self.scoreboard_menu.addstr(1, 1, f"Score: {self.score}")
        self.scoreboard_menu.refresh()
    
    def update_main_board(self, blocks=None):
        if blocks is None:
            blocks = self.blocks
        for y in range(len(blocks)):
            self.main_board.addstr(y + 1, 1, ''.join([SQUARE if x else EMPTY_BLOCK for x in blocks[y]]))
        # for y in range(len(self.blocks)):
        #     for x in range(len(self.blocks[0])):
        #         if self.blocks[y][x]: self.main_board.addstr(y + 1, x*2 + 1, SQUARE)
        self.main_board.refresh()

    def create_all_boards(self):
        self.create_scoreboard()
        self.create_main_board()
        self.create_right_menu()
        self.create_block_hold_menu()
        self.create_instructions_menu()
        self.scoreboard_menu.addstr(1, 1, f"Score: {self.score}")

    def update_next_block(self):
        self.right_menu.clear()
        self.right_menu.box()
        next_block = self.next_block.return_block()
        self.right_menu.addstr(1, 1, "Next Block:")
        for y in range(len(next_block)):
            self.right_menu.addstr(RIGHT_MENU_HEIGHT//3 + y + 1, RIGHT_MENU_WIDTH//3 + 2, ''.join([SQUARE if x else EMPTY_BLOCK for x in next_block[y]]))
        self.right_menu.refresh()

    def create_right_menu(self):
        self.right_menu.box()

    def create_main_board(self):
        self.main_board.box()

    def create_scoreboard(self):
        self.scoreboard_menu.box()
    
    def create_block_hold_menu(self):
        self.block_hold_menu.box()
        self.block_hold_menu.addstr(1, 1, "Holding:")
    
    def create_instructions_menu(self):
        self.instructions_menu.box()
        self.instructions_menu.addstr(1,1, "Key Bindings:")
        self.instructions_menu.addstr(3,1, "LEFT/RIGHT: Movement")
        self.instructions_menu.addstr(4,1, "UP: rotate clws")
        self.instructions_menu.addstr(5,1, "DOWN: fast drop")
        self.instructions_menu.addstr(6,1, "c: Hold")
        self.instructions_menu.addstr(7,1, "z: rotate anticlws")
        self.instructions_menu.addstr(8,1, "<space>: hard drop")

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
GAME_RUNNING = 0


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
