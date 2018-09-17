#!/usr/bin/env python3
import sys
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD
from time import sleep
import LoRaWAN,json,time,threading
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
        print(payload)
        lorawan = LoRaWAN.new(nwskey, appskey)
        lorawan.read(payload)
        lorawan.get_payload()
        self.write_config()
        self.write_log()
        sys.exit(0)

    def show(self, a) :
        print(','.join('0x'+format(x, '02x') for x in a))

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


    def send(self):
        global PARKING_NUMBER
        lorawan = LoRaWAN.new(nwskey, appskey)
        PARKING_NUMBER = str(self.get_parking_number())
        lorawan.create(MHDR.CONF_DATA_UP, {'devaddr': devaddr, 'fcnt': fCnt, 'data': list(map(ord, PARKING_NUMBER)) })
        self.set_dio_mapping([1,0,0,0,0,0])
        self.set_invert_iq(0)
        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)

    def read_config(self):
        global devaddr,nwskey,appskey,fCnt
        config_file = open('config.json')
        parsed_json = json.load(config_file)
        print(parsed_json['devaddr'])
        print(parsed_json['nwskey'])
        print(parsed_json['appskey'])
        print(parsed_json['fCnt'])
        devaddr = parsed_json['devaddr']
        nwskey = parsed_json['nwskey']
        appskey = parsed_json['appskey']
        fCnt = parsed_json['fCnt']

    def write_config(self):
        global fCnt
        fCnt = fCnt + 1
        config = {'devaddr':devaddr,'nwskey':nwskey,'appskey':appskey,'fCnt':fCnt}
        data = json.dumps(config)
        fp = open("config.json","w")
        fp.write(data)
        fp.close()

    def write_log(self):
        log = "[SEND] " + time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
        if RXDONE == True :
            log += " Send Success , Parking number : " + PARKING_NUMBER + "\n"
        else:
            log += " Send Failure , Retry " + str(RETRY)  + " time \n"
        fp = open("lora.log","a")
        fp.write(log)
        fp.close()

    def start(self):
        self.read_config()
        self.send()
        while True:
            if TIMER_START == True:
                t = threading.Thread(target = detector)
                t.start()
                t.join()
                if RXDONE == False:
                    global RETRY
                    lora.write_log()
                    RETRY = RETRY + 1
                    if RETRY >= MAX_RETRY:
                        print("Over retry limit!!")
                        sys.exit()
                    else:
                        lora.send()
            sleep(1)

def detector():
    for i in range(5):
        print("waiting {} second".format(i))
        if RXDONE == True:
            break
        time.sleep(1)
 

# Init
MAX_RETRY = 3
RETRY = 0
RXDONE = False
TIMER_START = False
CAR = 0

devaddr = []
nwskey = []
appskey = []
fCnt = 0

lora = LoRaWANotaa(False)

# Setup
parser.parse_args(lora)
lora.set_mode(MODE.SLEEP)
lora.set_dio_mapping([1,0,0,0,0,0])
#lora.set_freq(923.2)
#lora.set_bw(7)
#lora.set_spreading_factor(7)
lora.set_pa_config(pa_select=1)
lora.set_pa_config(max_power=0x0F, output_power=0x0E)
lora.set_invert_iq(0)
lora.set_sync_word(0x34)
lora.set_rx_crc(True)

#print(lora)
assert(lora.get_agc_auto_on() == 1)

try:
    print("Sending LoRaWAN Confirm Data\n")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("\nKeyboardInterrupt")
finally:
    sys.stdout.flush()
    lora.set_mode(MODE.SLEEP)
    BOARD.teardown()
