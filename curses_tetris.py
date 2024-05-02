import time
import random
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
GAME_RUNNING = 0


class Board:
    def __init__(self):
        """ Initializes the Board Object 
        The main logic and display for the Tetris game.

        Board Object will have:
        - a matrix/list of lists full of zeros as blocks
        - a GAME score as score
        - a Block object as current_block
        - a scoreboard menu
        - the main board where the matrix will be displayed
        - the right board where the next piece will be displayed
        - the left board where the block on hold will be displayed
        - an instructions menu

        Using curses:
        - block the keyboard input and cursor from displaying on the terminal

        Set variables for:
        - controlling and tracking gravity and events within the game
        - controlling the speed of the block
        - counting the number of lines cleared in a single gme
        - creating the next Block object so it can be displayed before it is inserted in the board
        - controlling the number of holdable blocks
        - determining if the user's currently holding a block
        - checking if the block is immediately on the top.
        """
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
        self.proc_event = None
        self.timing = 0.5
        self.lines_cleared = 0
        self.next_block = Block(START_X, START_Y)

        self.can_hold = 0
        self.block_held = None
        self.hard_dropped = 0


    def game_over(self):
        """ Closes the game officially. 
        Resets the score and sets a conditional Flag to false so the program quits
        """
        global GAME_RUNNING
        self.score = 0
        GAME_RUNNING = 0
        self.stdscr.addstr("Game Over! (Ctrl+C)")
        print("Game Over!")


    def start_game(self):
        """ Starts the game. 
        Main Systematic logic of a generic game.
        Runs the Tetris logic:
        - sets the conditional flag to true and initializes the display boards for the game.
        - creates the first block object
        - begins the Tetris game loop
        """
        global GAME_RUNNING
        GAME_RUNNING = 1
        self.create_all_boards()
        self.get_new_block()
        self.update_board()


    def is_gameover(self):
        """ Checks if the current block overlaps with any units of the accumulated blocks.
        Called every time after a block has reached the base to detect if the blocks have reached the top of the board
        Returns:
            Boolean: True if any unit of the inserted block shares a space in the matrix with any existing populated unit
        """
        block = self.current_block.return_block()
        block_height = len(block)

        for height in range(block_height):
            for width in range(len(block[0])):
                if block[height][width] and self.blocks[START_Y + height][START_X + width]:
                    return True
        return False


    def check_collision(self, new_x, new_y):
        """ Checks if the block can continue moving in the given direction by the new_x new_y coordinates

        Args:
            new_x (int): the index of the column of the row that the block is moving towards x/9
            new_y (int): the index of the row of the matrix the block is moving towards y/19
            **9 and 19 symbolize the index max in the 20*10 matrix that makes up the board. 

        Returns:
            boolean: True (meaning there is a collision) if the block and the next unit in the direction 
            it is moving towards are both populated. 
        """
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
    

    def block_gravity(self, event):
        """ Moves block down 1 unit for every interval. 
        Run by a background Thread througout the entirety of the block's moving lifespan.
        Called by the get_new_block function.
        Note that this function calls its parent function. But it checks if the game is over so it breaks the infinite loop. 

        Args:
            event (threading.Event()): the running Thread that will be set when the get_new_block function is called again. 
            
        """
        global GAME_RUNNING
        time.sleep(self.timing)
        while GAME_RUNNING and not event.is_set():
            # loop breaks get_new_block function gets called on a hard drop and the event gets set 
            # otherwise it breaks when a collision occurs. 
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
            time.sleep(self.timing)
        if GAME_RUNNING and not event.is_set():
            # only runs if loop broke by collision
            self.get_new_block()
            self.check_lines()


    def get_new_block(self):
        """ Creates a new block, ends the previous Thread, and starts a new Thread that moves the block down. 

        """
        self.can_hold = 1
        self.blocks = deepcopy(self.blocks_copy)
        self.current_block = self.next_block
        self.next_block = Block(START_X, START_Y)
        self.update_next_block()
        self.insert_block_into_board(self.current_block.get_x(), self.current_block.get_y())
        if self.gravity_proc is not None: # Ensures that only 1 block_gravitythread is running at a time
            if self.gravity_proc.is_alive(): self.proc_event.set() # sets the previous thread to set so that block_gravity function will exit from the while loop
        self.proc_event = threading.Event()
        self.gravity_proc = threading.Thread(target=self.block_gravity, args=(self.proc_event,))
        self.gravity_proc.start()

    def update_board(self):
        """Rotates, or moves the block depending on the user's keyboard input. 
        Also contains the functions for hard dropping, rotating anti-clockwise and holding the block
        """
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
        """Inserts the blocks into the board starting at x,y position. 
        converts the respective units to 1s and 0s to display the correct block shape       

        Args:
            x (int): the index of the column at which the block is to be inserted
            y (_type_): the index of the row in the matrix at which the block is to be inserted
        """
        block = self.current_block.return_block()
        block_height = len(block)
        self.blocks_copy = deepcopy(self.blocks)

        for height in range(block_height):
            for width in range(len(block[0])):
                if block[height][width]:
                    self.blocks_copy[y + height][x + width] = 1


    def shift_block(self, new_x, new_y):
        """Shifts the block to start from the new_x,new_y coordinates
        Inserts the block into the updated position and displays the updated view

        Args:
            new_x (int): the index of the column at which the block is to be inserted
            new_y (int): the index of the row in the matrix at which the block is to be inserted
        """
        self.current_block.update_x(new_x)
        self.current_block.update_y(new_y)
        self.insert_block_into_board(self.current_block.get_x(), self.current_block.get_y())
        self.update_main_board(self.blocks_copy)


    def change_position(self, is_right):
        """Moves the block right or left
        Only moves the block if it is within the bounds of the main board

        Args:
            is_right (bool): Indicator of whether the block is moving right or left
        """
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
        """Rotates the block clockwise(default)

        Args:
            clockwise (int, optional): If 0 rotates anti-clockwise, otherwise, rotates clockwise. Defaults to 0.
        """
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
        """Checks for full rows, clears them, and adds an empty row to the top of the matrix
        """
        lines = []
        for line_num in range(len(self.blocks)):
             if len(self.blocks[line_num]) == sum(self.blocks[line_num]):
                lines.append(line_num)
        if len(lines) != 0:
            self.clear_lines(lines)


    def clear_lines(self, lines):
        """Clears all the lines in the main board given by the lines array 
        Adds the default 0 rows to the top for every cleared line
        Calculates the points won and increases the score on the board. 
        
        Args:
            lines (array): A list containing the indeces of all the full rows
        """
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
        """Drops Block straight down to the top of the accumulated blocks 
        """
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
        self.get_new_block()
        self.check_lines()
        

    def hold_block(self):
        """Moves block from main board to holding space 
        If applicable, swaps block from holding space with block in the main board
        If there are no blocks in holding space, move current block and insert new block into main board.
        """
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
        """Displays the current block in the holding menu, (if applicable)
        """
        self.block_hold_menu.clear()
        self.block_hold_menu.box()
        self.block_hold_menu.addstr(1, 1, "Holding:")
        block = self.block_held.return_block()
        for y in range(len(block)):
            self.block_hold_menu.addstr(BLOCK_HOLD_HEIGHT//3 + y + 1, BLOCK_HOLD_WIDTH//3 + 2, ''.join([SQUARE if x else EMPTY_BLOCK for x in block[y]]))

        self.block_hold_menu.refresh()


    def update_score(self):
        """Displays the current score on the scoreboard
        """
        self.scoreboard_menu.addstr(1, 1, f"Score: {self.score}")
        self.scoreboard_menu.refresh()

    def update_main_board(self, blocks=None):
        """Merges the bottom of the board with the accumulated blocks to form a new bottom to allow for checking collisions

        Args:
            blocks (array, optional): _description_. Defaults to None.
        """
        if blocks is None:
            blocks = self.blocks
        for y in range(len(blocks)):
            self.main_board.addstr(y + 1, 1, ''.join([SQUARE if x else EMPTY_BLOCK for x in blocks[y]]))
        # for y in range(len(self.blocks)):
        #     for x in range(len(self.blocks[0])):
        #         if self.blocks[y][x]: self.main_board.addstr(y + 1, x*2 + 1, SQUARE)
        self.main_board.refresh()


    def create_all_boards(self):
        """Creates all the necessary display boards for the functionality of the game
        """
        self.create_scoreboard()
        self.create_main_board()
        self.create_right_menu()
        self.create_block_hold_menu()
        self.create_instructions_menu()
        self.scoreboard_menu.addstr(1, 1, f"Score: {self.score}")


    def update_next_block(self):
        """Updates the block displayed in the next block menu
        When a new block is created, the next block becomes the current block and a new next_block is generated. 
        The function updates the displayed block in the top right menu
        """
        self.right_menu.clear()
        self.right_menu.box()
        next_block = self.next_block.return_block()
        self.right_menu.addstr(1, 1, "Next Block:")
        for y in range(len(next_block)):
            self.right_menu.addstr(RIGHT_MENU_HEIGHT//3 + y + 1, RIGHT_MENU_WIDTH//3 + 2, ''.join([SQUARE if x else EMPTY_BLOCK for x in next_block[y]]))
        self.right_menu.refresh()


    def create_right_menu(self):
        """creates the next block menu where the next block will be displayed"""
        self.right_menu.box()


    def create_main_board(self):
        """Creates the 20x10 main board where the blocks wil drop
        """
        self.main_board.box()


    def create_scoreboard(self):
        """creates the board where the score will be displayed
        """
        self.scoreboard_menu.box()


    def create_block_hold_menu(self):
        """Creates the board on the top left where the holding block will be displayed
        """
        self.block_hold_menu.box()
        self.block_hold_menu.addstr(1, 1, "Holding:")


    def create_instructions_menu(self):
        """Creates an instructions menu with the hotkeys so users can learn how to play on the fly.
        """
        self.instructions_menu.box()
        self.instructions_menu.addstr(1,1, "Key Bindings:")
        self.instructions_menu.addstr(3,1, "LEFT/RIGHT: Movement")
        self.instructions_menu.addstr(4,1, "UP: rotate clws")
        self.instructions_menu.addstr(5,1, "DOWN: fast drop")
        self.instructions_menu.addstr(6,1, "c: Hold")
        self.instructions_menu.addstr(7,1, "z: rotate anticlws")
        self.instructions_menu.addstr(8,1, "<space>: hard drop")


    def get_self_blocks(self):
        """Returns the list of lists of the saved main board before the last inserted block

        Returns:
            list of lists: Contains the matrix of the last saved main board.
        """
        return self.blocks
    

    def get_current_blocks(self):
        """Returns the current moving block or the last inserted block

        Returns:
            list of lists: contains the matrix of the current block 
        """
        return self.current_block


class Block:
    def __init__(self, x, y):
        """Initializing the block class
        Consists of:
        - a block type (of the 7 tetris block shapes)
        - an array of 1s and 0s in the shape of the given block (from the BLOCKS array)
        - height of the block
        - width of the block
        - horizontal coordinates of the block in the matrix as X
        - vertical coordinates of the block in the matrix as y
        
        Args:
            x (int): the index of the column at which the block is to be inserted
            y (int): the index of the row in the matrix at which the block is to be inserted
        """
        self.block_type = random.randint(0, NUM_OF_BLOCK_TYPES - 1)
        self.block = BLOCKS[self.block_type]
        self.height = len(self.block)
        self.width = len(self.block[0])
        self.x = x
        self.y = y


    def create_nblock(self, given_block):
        """Displays the block from the block array

        Args:
            given_block (list of lists): Selected permutation from BLOCKS array

        Returns:
            string: Display characters for given block permutation
        """
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
        """Rotates the block anticlockwise preserving its shape"""
        self.block = [[self.block[j][i] for j in range(len(self.block))] for i in range(len(self.block[0]) - 1, -1, -1)]


    def rotate_clockwise(self):
        """Rotates the block clockwise preserving its shape"""
        for _ in range(3):
            self.rotate_anticlockwise()


    def return_block(self):
        """Returns the block permutation (can be either one of those from the BLOCKS array in any one of its rotated orientations)

        Returns:
            list of lists: current block with its preserved rotation state
        """
        return self.block
    
    
    def get_x(self):
        """Gets the index of the column at which the block is 

        Returns:
            int: the index of the column at which the block is 
        """
        return self.x


    def get_y(self):
        """Gets the index of the row at which the block is

        Returns:
            int: the index of the column at which the block is 
        """
        return self.y


    def get_height(self):
        """Gets the height of the block

        Returns:
            int: number of rows in the block permutation
        """
        return self.height


    def get_width(self):
        """Gets the width of the block

        Returns:
            int: number of columns in the block permutation
        """
        return self.width
    

    def update_x(self,x):
        """updates the index of the column at which the block is 

        Args:
            x (int): the index of the column in the matrix that the block is
        """
        self.x = x
        

    def update_y(self, y):
        """updates the index of the row at which the block is 

        Args:
            x (int): the index of the row in the matrix that the block is
        """

        self.y = y


def signal_handler(sig, frame):
    """Resets the conditional flag and ends the program 

    Args:
        sig (int): A signal int code that would trigger this function
        frame (obj): a frame object
    """
    global GAME_RUNNING
    print("Exiting")
    GAME_RUNNING = 0


def main():
    """main function of this python program that creates the board class and starts the game.
    """
    BOARD = Board()
    signal.signal(signal.SIGINT, signal_handler)
    BOARD.start_game()
    

if __name__=="__main__":
    main()
