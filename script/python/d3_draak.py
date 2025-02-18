#! /usr/bin/env python3
#===============================
#
# d3-draak
#
# 2022/03/28 Kuninori Morimoto <kuninori.morimoto.gx@renesas.com>
#===============================
import sys
import time

import base
#====================================
#
# board
#
#====================================
class board(base.board):
    #--------------------
    # select_soc
    #--------------------
    def __select_soc(self):
        self.__select_soc_noselect()

    #--------------------
    # __init__
    #--------------------
    def __init__(self, ver="", tty=""):

        super().__init__(soc="d3", rom="yocto", ver=ver, tty=tty)

        self.confirm_location()
        self.config_load()
        self.setup()

        self.confirm_info()
        self.config_save()
        self.check_files()

#====================================
#
# rom_write_guide
#
#====================================
class rom_write_guide(base.guide):
    #--------------------
    # __init__
    #--------------------
    def __init__(self, board):
        super().__init__(board.tty(), 115200)
        # possible to use from child-class
        self.board = board

    #--------------------
    # guide_start
    #--------------------
    def guide_start(self):
        sw = base.switch(self.board.dir_config("sw"))

        # power off
        self.power("OFF")
        self.ask_yn()

        # indicate dip-switch update mode
        sw.print_msg_update()
        self.ask_yn()

        self.power("ON")
        self.expect(">")

        # indicate dip-switch normal mode
        sw.print_msg_normal()
        self.ask_yn()

        # speed up
        self.speed_up("921.6Kbps", 921600)

        # main loop
        self.sk_type_main_loop(self.board.addr_map(), "3", 3, self.ask_loop())
        self.msg("finished !!")

#====================================
#
# As command
#
#	> draak yocto		# yocto
#	> draak			# test
#
#====================================
if __name__=='__main__':
    if (len(sys.argv) < 2):
        # test
        board(ver="5.9.0", tty="/dev/ttyUSB0")
        sys.exit(0)
    if (sys.argv[1] == "yocto"):
        rom_write_guide(board()).guide_start()
    else:
        print("unknown command")
