#!/usr/bin/env python3
import sys
from time import sleep
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD
import LoRaWAN,json,time
from LoRaWAN.MHDR import MHDR
from random import randrange

BOARD.setup()
parser = LoRaArgumentParser("LoRaWAN sender")

class LoRaWANotaa(LoRa):
    def __init__(self, verbose = False):
        super(LoRaWANotaa, self).__init__(verbose)

    def on_rx_done(self):
        print("RxDone")
        global RXDONE
        RXDONE = True
        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True)
        lorawan = LoRaWAN.new([],appkey)
        lorawan.read(payload)
        lorawan.get_payload()
        lorawan.get_mhdr().get_mversion()

        if lorawan.get_mhdr().get_mtype() == MHDR.JOIN_ACCEPT:
            print("Got LoRaWAN join accept")
            devaddr = lorawan.get_devaddr()
            nwskey = lorawan.derive_nwskey(devnonce)
            appskey = lorawan.derive_appskey(devnonce)
            self.show("DevAddr : ",devaddr)
            self.show("Network Session Key : ",nwskey)
            self.show("Application Session Key : ",appskey)
            self.write_config(devaddr,nwskey,appskey)
            self.write_log()
            sys.exit(0)

    def show(self,s,a) :
        print(s + (','.join('0x'+format(x, '02x') for x in a)))

    def write_config(self,devaddr,nwskey,appskey):
        config = {'devaddr':devaddr,'nwskey':nwskey,'appskey':appskey,'fCnt':0}
        data = json.dumps(config)
        fp = open("config.json","w")
        fp.write(data)
        fp.close()

    def write_log(self):
        log = "[JOIN] " + time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
        if RXDONE == True:
            log += " Join Success\n"
        else:
            log += " Join Failure , Retry " + str(RETRY)  + " time\n"
        fp = open("lora.log","a")
        fp.write(log)
        fp.close()

    def on_tx_done(self):
        self.clear_irq_flags(TxDone=1)
        print("TxDone")
        self.set_mode(MODE.STDBY)
        self.set_dio_mapping([0,0,0,0,0,0])
        self.set_invert_iq(1)
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)
        global TIMER_START
        TIMER_START = True

    def join(self):
        lorawan = LoRaWAN.new(appkey)
        lorawan.create(MHDR.JOIN_REQUEST, {'deveui': deveui, 'appeui': appeui, 'devnonce': devnonce})
        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)


    def start(self):
        self.join()
        while True:
            if TIMER_START == True:
                detector()
                if RXDONE == False:
                    global RETRY
                    lora.write_log()
                    RETRY = RETRY + 1
                    if RETRY >= MAX_RETRY:
                        print("Over retry limit!!")
                        sys.exit()
                    else:
                        sleep(5)
                        lora.join()
            sleep(1)

def detector():
    for i in range(10):
        print("waiting {} second".format(i))
        if RXDONE == True:
            break
        time.sleep(1)

# Init
MAX_RETRY = 3
RETRY = 0
RXDONE = False
TIMER_START = False

deveui = [0x00,0x80,0x00,0x00,0x00,0x07,0x77,0x77]
appeui = [0x86,0xe4,0xef,0xc7,0x10,0x4f,0x68,0x29]
appkey = [0xa3,0x46,0xb6,0xfa,0xef,0x2b,0xd3,0x3c,0x16,0xfe,0x9b,0x1d,0x8d,0x47,0xa1,0x1d]
devnonce = [randrange(256), randrange(256)]#rand Devic address

lora = LoRaWANotaa(False)

# Setup
parser.parse_args(lora)
lora.set_mode(MODE.SLEEP)
lora.set_dio_mapping([1,0,0,0,0,0])
lora.set_freq(923.2)
lora.set_bw(7)
lora.set_spreading_factor(7)
lora.set_pa_config(pa_select=1)
lora.set_pa_config(max_power=0x0F, output_power=0x0E)
lora.set_invert_iq(0)
lora.set_sync_word(0x34)
lora.set_rx_crc(True)

#print(lora)
assert(lora.get_agc_auto_on() == 1)

try:
    print("Sending LoRaWAN join request\n")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("\nKeyboardInterrupt")
finally:
    sys.stdout.flush()
    lora.set_mode(MODE.SLEEP)
    BOARD.teardown()
