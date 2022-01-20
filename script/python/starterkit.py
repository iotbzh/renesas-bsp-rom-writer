#! /usr/bin/env python3
#===============================
#
# starterkit
#
# 2022/01/07 Kuninori Morimoto <kuninori.morimoto.gx@renesas.com>
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
    # __init__
    #--------------------
    def __init__(self, confirm, soc="", os="", ver="", tty="", mac=None):

        # mac is needed if Android
        if (os == "android"):
            mac = ""
        # mot setting file for dir_config()
        # ${renesas-bsp-rom-writer}/starterkit/config/mot
        mot_file = "mot"

        super().__init__("starterkit", soc=soc, os=os, ver=ver, tty=tty, mac=mac, mode="", mot_file=mot_file)

        self.config_load()
        self.setup()

        # confirm to user
        if (confirm):
            self.confirm_info()
        self.config_save()
        self.check_files()

    #--------------------
    # tty_connection
    # soc_explanation
    # mode_explanation
    #--------------------
    def tty_connection(self):
        return "\n".join(self.ttm_array(self.dir_config_os("connection"), "tty_connection"))
    def soc_explanation(self):
        return "\n".join(self.ttm_array(self.dir_config("soc"), "list_soc_explanation"))
    def mode_explanation(self):
        # We can't share mode explanation message on config file
        # because Linux vs Windows explanation are different
        return "normal: Need manual Dip-Switch settings to write ROM.\n" +\
               "        You need to select normal mode\n" +\
               "        if your current board has no ROM (no U-boot)\n" +\
               "mot:    No Dip-Switch settings are needed.\n" +\
               "        You need to run make and create mot first.\n" +\
               "             > cd ${renesas-bsp-rom-writer}\n" +\
               "             > make\n"

#====================================
#
# rom_write_guide
#
#====================================
class rom_write_guide(base.guide):

    #======================
    # <Overwrite>
    #
    # load_sw
    #
    # starterkit sw setting are located at
    # ${renesas-bsp-rom-writer}/starterkit/config/sw/${soc}
    #
    # Overwrite load_sw() if other board re-use rom_write_guide
    #======================
    def load_sw(self):
        return base.switch(self.board.dir_config_sw(self.board.soc()))

    #======================
    # <Overwrite>
    #
    # M2 v1 Starterkit doesn't need 2nd Y in main loop
    # Overwrite use_2nd_Y() if other board re-use rom_write_guide
    #======================
    def use_2nd_Y(self):
        if (self.board.soc_ws() == "m3_2g"):
            return False
        return True

    #--------------------
    # __init__
    #--------------------
    def __init__(self, board):
        super().__init__(board.tty(), 115200)
        # possible to use from child-class
        self.board = board

        self.__use_2nd_Y = self.use_2nd_Y()

    #--------------------
    # main loop
    #--------------------
    def main_loop(self):
        for map in self.board.addr_map():
            self.send()
            self.expect(">")

            self.send("xls2")

            self.expect("Select (1-3)>")
            self.send("3")

            self.expect("(Push Y key)")
            self.send("Y", end="")

            if (self.__use_2nd_Y):
                self.expect("(Push Y key)")
                self.send("Y", end="")

            self.expect("Please Input : H'")
            self.send(map["addr"])

            self.expect("Please Input : H'")
            self.send(map["save"])

            self.expect("please send !")
            self.send_file("{}/{}".format(self.cwd(), map["srec"]))

            self.expect("Clear OK?(y/n)")
            self.send("y", end="")

            self.expect(">")

        self.msg("finished !!")

    #--------------------
    # guide_for_mot
    #--------------------
    def guide_for_mot(self):
        mot_file = "{}/starterkit/config/mot".format(self.top())
        cpld_cmd = self.ttm_array(mot_file, "cpld_cmd")

        # power on
        # and stop the U-Boot autorun
        self.power("ON")
        self.stop_autorun()

        # just to be sure
        self.send()
        self.expect("=>")

        # send CPLD settings
        for cmd in cpld_cmd:
            self.send(cmd)
            self.expect("=>")

        # indicate meesage
        # and send mot file
        self.expect("please send !")
        self.send_file(self.board.mot())
        self.expect(">")

        # speed up
        self.speed_up("921.6Kbps", 921600)

        # main loop
        self.main_loop()

    #--------------------
    # guide_for_normal
    #--------------------
    def guide_for_normal(self):
        sw = self.load_sw()

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
        self.main_loop()

    #--------------------
    # guide_start
    #--------------------
    def guide_start(self):
        self.msg("Confirm serial connection.\n"\
                 "Please don't use USB hub between [PC] and [board].\n"\
                 "       ^^^^^^^^^^^^^^^^^\n\n" +\
                 self.board.tty_connection())
        self.ask_yn()

        # power off
        self.power("OFF")
        self.ask_yn()

        # normal/mot mode init
        if (self.board.mode() == "mot"):
            self.guide_for_mot()
        else:
            self.guide_for_normal()

#====================================
#
# fastboot_uboot_guide
#
#====================================
class fastboot_uboot_guide(base.guide):

    #--------------------
    # __init__
    #--------------------
    def __init__(self, board):
        super().__init__(board.tty(), 115200)

        # possible to use from child-class
        self.board = board

    #--------------------
    # erase_bootloader
    #--------------------
    def erase_bootloader(self):
        self.stop_autorun()

        self.send()
        self.expect("=>")

        self.send("mmc dev 1 1")
        self.expect("=>")

        self.send("mw.b 4f000000 0 200000")
        self.expect("=>")

        self.send("mmc write 4f000000 0 1000")
        self.expect("=>")

        self.send("mmc dev 1 2")
        self.expect("=>")

        self.send("mw.b 4f000000 0 200000")
        self.expect("=>")

        self.send("mmc write 4f000000 0 1000")
        self.expect("=>")

        self.send("reset")

        time.sleep(1)
        self.stop_autorun()

    #--------------------
    # setenv
    #--------------------
    def setenv(self):
        self.send()
        self.expect("=>")

        self.send("env default -a")
        self.expect("=>")

        self.send("setenv ethaddr {}".format(self.board.mac()))
        self.expect("=>")

        # use vague number for serialno :)
        self.send("setenv serialno 00009999")
        self.expect("=>")

        self.send("setenv bootargs video=LVDS-1:d video=VGA-1:d init_time={}".format(int(time.time())))
        self.expect("=>")

        self.send("saveenv")
        self.expect("=>")

        self.send("reset")

        time.sleep(1)
        self.stop_autorun()

    #--------------------
    # start_fastboot
    #--------------------
    def start_fastboot(self):
        self.send()
        self.expect("=>")

        self.send("fastboot")
        self.expect("USB")

    #--------------------
    # guide_start
    #--------------------
    def guide_start(self):
        self.msg("Confirm serial connection.\n"\
                 "Please don't use USB hub between [PC] and [board].\n"\
                 "       ^^^^^^^^^^^^^^^^^\n\n" +\
                 self.board.tty_connection())
        self.ask_yn()

        # power off
        self.power("OFF")
        self.ask_yn()

        # power off
        self.power("ON")

        self.erase_bootloader()
        self.setenv()
        self.start_fastboot()

#====================================
#
# As command
#
#	> starterkit yocto		# yocto
#	> starterkit android		# android
#	> starterkit --			# select os
#	> starterkit android_fastboot	# android fastboot for uboot
#	> starterkit			# test
#
#====================================
if __name__=='__main__':
    confirm	= 0
    os		= ""
    guide	= None

    if (not sys.argv[1]):
        # test
        board("h3_4g", os="yocto", ver="5.5.0", tty="/dev/ttyUSB0")
        sys.exit(0)
    if (sys.argv[1] == "yocto"):
        confirm = 1
        os = "yocto"
        guide = rom_write_guide
    elif (sys.argv[1] == "android"):
        confirm = 1
        os = "android"
        guide = rom_write_guide
    elif (sys.argv[1] == "android_fastboot"):
        confirm = 0
        os = "android"
        guide = fastboot_uboot_guide
    else:
        print("unknown command")
        sys.exit(1)

    guide(board(confirm, os=os)).guide_start()
