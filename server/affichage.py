import sys, pygame
import math
import paho.mqtt.client as mosquitto
from time import sleep
import json
'''
Little display of a mongodb database.
First fetching the content of the database
Then each time the database is modified displaying immediatly the changes
'''

mqtt_host = 'localhost'

# Vote configuration
scores = {-1: 0, 0: 0, 1: 0}
names = {1: 'Pour', -1: 'Contre', 0: 'Neutre'}

# Initialize PyGame screen
pygame.init()
size = width, height = 600, 600
screen = pygame.display.set_mode(size)
pygame.display.set_caption("Vote result")
h_bas = height - 10
myfont = pygame.font.SysFont("Comic Sans MS", 80)
pink = (255, 0, 255)
blue = (0, 255, 255)

#MQTT part
def on_message(client, data, msg):
    timestamp, uid, value = str(msg.payload).split(',')
    value = int(value)
    print "One more for", names[value]
    scores[value] += 1

mqttc = mosquitto.Mosquitto("nfc-vote-visu")
mqttc.on_message = on_message
mqttc.connect(mqtt_host, 1883)
mqttc.subscribe("nfc-vote", 0)

while 1:
    sleep(0.2)
    mqttc.loop()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            break
            
    screen.fill((0,0,0))
    
    max_score = max(scores.values())
    if max_score != 0:
        rapport = 500 / max_score
    else:
        rapport = 1
        
    for i, value in enumerate(scores.keys()):
        xx = 200 * i
        votes = scores[value]
        label = myfont.render(str(votes), 1, pink)
        title = myfont.render(names[value], 1, blue)
        
        screen.blit(pygame.transform.rotozoom(title,0,0.5), (xx + 60, 50))
        
        if votes == 0:
            screen.blit(pygame.transform.rotozoom(label,45,0.5), (xx + 82, 550))
            
        else:
            hauteur = votes * rapport
            
            rect = pygame.Rect(xx + 20, h_bas - hauteur, 160, hauteur)
            pygame.draw.rect(screen, (50,50,50), rect)
            screen.blit(pygame.transform.rotozoom(label,45,0.5),
                        (xx + 82 - math.log(votes,10)*7,
                         min(550,h_bas - hauteur + 20)))
    
    pygame.display.update()
