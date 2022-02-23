import pygame as pg
import sys
import math
import random
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from tkinter import *

pg.init()

SW, SH = 1280, 720
SC = pg.display.set_mode((SW, SH))
pg.display.set_caption("Smart balloons")
clock = pg.time.Clock()
FPS = 60
default_font = pg.font.SysFont(None, 40)
random.seed(42)
move_limit = 1800
generation_count = 0
frame_count = 0
success_count = 0
avg_fitness = 0
avg_fitness_diff = 0
lowest_time = 0
lowest_time_diff = 0
success_count_diff = 0
level_color = [random.randrange(150) + 100, random.randrange(150) + 100, random.randrange(150) + 100]
finished = False
walls = []
gene_pool = []
population_size = 100
balloons_alive = population_size
background = pg.image.load('images/sky.png').convert_alpha()

avg_fitness_lst = []
success_count_lst = []
avg_collision_lst = []
avg_won_time_lst = []
balloons_alive_lst = []

plt.style.use("bmh")
algo_colors = [
    "#429ae3",
    "#e67a37",
    "#80db7d",
    "#b33434",
    "#694087",
    "#7d5252",
    "#c981b8"
]


def show_text(string, x, y, size=40, color=(0, 0, 0)):
    func_font = pg.font.SysFont(None, size)
    SC.blit(func_font.render(string, True, color), (x, y))


# 0, 1280, 1, 0, dist
def remap(low1, high1, low2, high2, value):
    return low2 + (value - low1) * (high2 - low2) / (high1 - low1)


def distance(x1, x2, y1, y2):
    return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))


class Obstacle(object):
    def __init__(self, x, y, width, height):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.subsurface = pg.Surface((self.width, self.height))

    def draw(self):
        pg.draw.rect(SC, (150, 150, 150), (self.x, self.y, self.width, self.height))


class ArcObstacle(object):
    def __init__(self, x, y, width, height, start_angle, stop_angle):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.subsurface = pg.Surface((self.width, self.height))
        self.start_angle, self.stop_angle = start_angle, stop_angle

    def draw(self):
        pg.draw.arc(SC, (150, 150, 150), (self.x, self.y, self.width, self.height),
                    self.start_angle, self.stop_angle, 15)


class DNA(object):
    def __init__(self, genes=None):
        self.array = []
        self.chain = pg.math.Vector2()
        if genes:
            self.array = genes
        else:
            for i in range(move_limit):
                self.chain.xy = random.random() * 2 - 1, random.random() * 2 - 1
                self.array.append(self.chain.xy)

    def crossover(self, partner):
        child_chromosome = []
        middle = math.floor(random.randrange(len(self.array)))
        for i in range(len(self.array)):
            if i < middle:
                child_chromosome.append(self.array[i])
            else:
                child_chromosome.append(partner.array[i])
        return DNA(child_chromosome)

    def mutation(self, mutation_rate):
        for i in range(len(self.array)):
            if random.uniform(0, 1) < mutation_rate:
                mutated_gene = pg.math.Vector2()
                mutated_gene.xy = random.random() * 2 - 1, random.random() * 2 - 1
                self.array[i] = mutated_gene


class Balloon(object):
    def __init__(self, dna=None):
        self.alive = True
        self.crashed = False
        self.won = False
        self.won_time = -1
        self.collision_count = 0
        self.coin_count = 0
        self.coin_ckpt = []

        if dna:
            self.gene = DNA(dna)
        else:
            self.gene = DNA()

        self.x, self.y = 25, SH // 2
        self.size = 10
        self.acc = pg.math.Vector2()
        self.acc.xy = 0, 0
        self.vel = pg.math.Vector2()
        self.vel.xy = 0, 0
        self.vel_limit = 4
        self.burstColor = pg.Color("red")
        self.burstSize = 10
        self.fitness = 0
        self.subsurface = pg.Surface((self.size, self.size))
        self.subsurface.fill((50, 215, 240))
        self.subsurface.set_alpha(128)

        # self.image = pg.image.load('hot-air-balloon16.png').convert()
        self.image = pg.image.load('images/hot-air-balloon.png')
        self.image = pg.transform.scale(self.image, (25, 25))

    def check_boundary_collision(self):
        if self.x + self.size > SW or self.x < 0 or self.y < 0 or self.y + self.size > SH:
            self.crashed = True
            self.alive = False

    def check_wall_collision(self, arr):
        for item in arr:
            if self.subsurface.get_rect(topleft=(self.x, self.y)). \
                    colliderect(item.subsurface.get_rect(topleft=(item.x, item.y))):
                self.collision_count += 1
                self.x += -(self.vel.x * 1.2)
                self.y += -(self.vel.y * 1.2)
                self.vel.x -= self.acc.x
                self.vel.y -= self.acc.y

    def check_enemy_collision(self, arr):
        global balloons_alive

        for item in arr:
            if self.subsurface.get_rect(topleft=(self.x, self.y)). \
                    colliderect(item.subsurface.get_rect(topleft=(item.x, item.y))):
                self.crashed = True
        if self.crashed:
            self.alive = False
            balloons_alive -= 1

    def check_coin_collision(self, arr):
        for idx, item in enumerate(arr):
            if self.subsurface.get_rect(topleft=(self.x, self.y)). \
                    colliderect(item.subsurface.get_rect(topleft=(item.x, item.y))) and idx not in self.coin_ckpt:
                self.coin_count += 1
                self.coin_ckpt.append(idx)

    def calculate_fitness(self):
        dist = distance(self.x, finish.x, self.y, finish.y)
        dist_score = remap(0, SW, 1, 0, dist)
        collision_score = remap(0, move_limit, 1, 0, self.collision_count)
        self.fitness = (dist_score * 100 * 0.85) + (self.coin_count * (100 / len(levels[level]['coins'])) * 0.15)  # - \
        # (collision_score * 100 * 0.2)

    def update(self):
        if self.crashed:
            self.image = pg.image.load('images/explosion.png')  # .convert()  # or .convert_alpha()
            self.image = pg.transform.scale(self.image, (16, 16))
            # self.image.fill((0, 0, 0, 0))
            SC.blit(self.image, (self.x, self.y))
            # self.subsurface.fill((128, 0, 0))  # If crashed, turn it's color to red.

        if self.alive:
            self.acc = self.gene.array[frame_count]

            if self.subsurface.get_rect(topleft=(self.x, self.y)).colliderect(win_rect) and not self.won:
                self.won = True
                self.won_time = frame_count

            if self.won:
                self.x, self.y = finish.x, finish.y
                self.vel.xy = 0, 0
                self.acc.xy = 0, 0

        self.vel += self.acc
        if self.vel.x > self.vel_limit and self.acc.x > 0:
            self.vel.x = self.vel_limit
        if self.vel.x < -self.vel_limit and self.acc.x < 0:
            self.vel.x = -self.vel_limit
        if self.vel.y > self.vel_limit and self.acc.y > 0:
            self.vel.y = self.vel_limit
        if self.vel.y < -self.vel_limit and self.acc.y < 0:
            self.vel.y = -self.vel_limit
        self.x += self.vel.x
        self.y += self.vel.y

    def draw(self):
        SC.blit(self.image, (self.x, self.y))


finish = pg.math.Vector2()
finish.xy = SW - 100, SH // 2
win_surface = pg.Surface((80, 80))
win_rect = win_surface.get_rect(topleft=(finish.x - 40, finish.y - 40))
balloon_population = []

for i in range(population_size):
    balloon_population.append(Balloon())


def finish_generation():
    global finished, avg_fitness, move_limit, walls, success_count
    global generation_count, frame_count, lowest_time, balloon_population, gene_pool
    global level_color, avg_fitness_diff, lowest_time_diff, success_count_diff, balloons_alive

    temp_lowest_time = lowest_time
    temp_avg_fitness = avg_fitness
    temp_success_count = success_count
    gene_pool.clear()

    max_fit = 0
    lowest_time = move_limit
    lowest_index = 0
    success_count = 0
    avg_fitness_sum = 0
    avg_collision_sum = 0
    avg_won_time_sum = 0
    avg_coin_sum = 0
    max_fit_index = 0

    for i, balloon in enumerate(balloon_population):
        balloon.calculate_fitness()
        avg_fitness_sum += balloon.fitness
        avg_collision_sum += balloon.collision_count
        if balloon.won:
            success_count += 1
            avg_won_time_sum += balloon.won_time
            avg_coin_sum += 1

            if balloon.won_time < lowest_time:
                lowest_time = balloon.won_time
                lowest_index = i

        if balloon.fitness > max_fit:
            max_fit = balloon.fitness
            max_fit_index = balloon_population.index(balloon)

    lowest_time_diff = lowest_time - temp_lowest_time

    success_count_diff = success_count - temp_success_count
    avg_fitness = avg_fitness_sum / len(balloon_population)
    avg_collision = avg_collision_sum / len(balloon_population)
    avg_won_time = avg_won_time_sum / len(balloon_population)
    avg_coin = avg_coin_sum / len(balloon_population)
    avg_fitness_diff = avg_fitness - temp_avg_fitness

    avg_fitness_lst.append(avg_fitness)
    success_count_lst.append(success_count)
    avg_collision_lst.append(avg_collision)
    avg_won_time_lst.append(avg_won_time)
    balloons_alive_lst.append(balloons_alive)

    for i, balloon in enumerate(balloon_population):
        n = int((balloon.fitness * 0.5))
        if balloon.won and success_count > 2:
            n = int(balloon.fitness * 5)
        if i == max_fit_index:
            if success_count < 2:
                n = int(balloon.fitness * 3)
        if i == lowest_index and success_count > 1:
            n = int(balloon.fitness * 15)
        if balloon.won and success_count <= 2:
            n = int(balloon.fitness * 20)
        for j in range(n):
            gene_pool.append(balloon_population[i])

        # n = int((balloon.fitness * 0.25))
        # if i == max_fit_index:
        #     if success_count < 2:
        #         n = int(balloon.fitness * 3)
        # if balloon.won:
        #     n = int(balloon.fitness * 20)
        # if i == lowest_index and success_count > 1:
        #     n = int(balloon.fitness * 50)
        # for j in range(n):
        #     gene_pool.append(balloon_population[i])

    if generation_count == gen_nb:
        d = {'Geração': list(range(generation_count + 1)), 'Valor de fitness médio': avg_fitness_lst}
        df = pd.DataFrame(d)

        sns.set(font_scale=1.2, style="whitegrid")

        fitness_plot = sns.relplot(
            x='Geração',
            y='Valor de fitness médio',
            data=df,
            kind="line",
            lw=3,
            palette=algo_colors,
            markers=True,
            dashes=False
        )
        fitness_plot.set_axis_labels("Geração", "Valor de fitness médio")
        fitness_plot.fig.suptitle('Gráfico da função fitness')
        fitness_plot.fig.title_fontsize = 18
        fitness_plot.fig.set_size_inches((12, 8))
        fitness_plot.savefig('./results/' + level + '/fitness_plot.png')

        d = {'Geração': list(range(generation_count + 1)), 'Sucessos': success_count_lst}
        df = pd.DataFrame(d)

        success_plot = sns.relplot(
            x='Geração',
            y='Sucessos',
            data=df,
            kind="line",
            lw=3,
            palette=algo_colors,
            markers=True,
            dashes=False
        )
        success_plot.set_axis_labels("Geração", "Sucessos")
        success_plot.fig.suptitle('Gráfico do número de sucessos')
        success_plot.fig.title_fontsize = 18
        success_plot.fig.set_size_inches((12, 8))
        success_plot.savefig('./results/' + level + '/success_plot.png')

        d = {'Geração': list(range(generation_count + 1)), 'Número médio de colisões': avg_collision_lst}
        df = pd.DataFrame(d)

        collision_plot = sns.relplot(
            x='Geração',
            y='Número médio de colisões',
            data=df,
            kind="line",
            lw=3,
            palette=algo_colors,
            markers=True,
            dashes=False
        )
        collision_plot.set_axis_labels("Geração", "Número médio de colisões")
        collision_plot.fig.suptitle('Gráfico da média de colisões')
        collision_plot.fig.title_fontsize = 18
        collision_plot.fig.set_size_inches((12, 8))
        collision_plot.savefig('./results/' + level + '/collision_plot.png')

        d = {'Geração': list(range(generation_count + 1)), 'Tempo médio de término': avg_won_time_lst}
        df = pd.DataFrame(d)

        sns.set(font_scale=1.2, style="whitegrid")

        time_plot = sns.relplot(
            x='Geração',
            y='Tempo médio de término',
            data=df,
            kind="line",
            lw=3,
            palette=algo_colors,
            markers=True,
            dashes=False
        )
        time_plot.set_axis_labels("Geração", "Tempo médio de término")
        time_plot.fig.suptitle('Gráfico do tempo gasto dos indivíduos com sucesso')
        time_plot.fig.title_fontsize = 18
        time_plot.fig.set_size_inches((12, 8))
        time_plot.savefig('./results/' + level + '/time_plot.png')

        d = {'Geração': list(range(generation_count + 1)), 'Moedas coletadas': avg_coin}
        df = pd.DataFrame(d)

        sns.set(font_scale=1.2, style="whitegrid")

        coin_plot = sns.relplot(
            x='Geração',
            y='Moedas coletadas',
            data=df,
            kind="line",
            lw=3,
            palette=algo_colors,
            markers=True,
            dashes=False
        )
        coin_plot.set_axis_labels("Geração", "Moedas coletadas")
        coin_plot.fig.suptitle('Gráfico de moedas coletadas')
        coin_plot.fig.title_fontsize = 18
        coin_plot.fig.set_size_inches((12, 8))
        coin_plot.savefig('./results/' + level + '/coin_plot.png')

        d = {'Geração': list(range(generation_count + 1)), 'Indivíduos vivos': balloons_alive_lst}
        df = pd.DataFrame(d)

        sns.set(font_scale=1.2, style="whitegrid")

        alive_balloons_plot = sns.relplot(
            x='Geração',
            y='Indivíduos vivos',
            data=df,
            kind="line",
            lw=3,
            palette=algo_colors,
            markers=True,
            dashes=False
        )
        alive_balloons_plot.set_axis_labels("Geração", "Indivíduos vivos")
        alive_balloons_plot.fig.suptitle('Gráfico do número de indivíduos vivos')
        alive_balloons_plot.fig.title_fontsize = 18
        alive_balloons_plot.fig.set_size_inches((12, 8))
        alive_balloons_plot.savefig('./results/' + level + '/balloons_alive_plot.png')

        pg.quit()
        sys.exit()

    else:
        generation_count += 1
        new_generation = []
        winners = []
        for balloon in balloon_population:
            if balloon.won:
                winners.append(balloon)

        winners = sorted(winners, key=lambda x: x.fitness, reverse=True)
        s = int((10 * population_size) / 100)

        for idx, winner in enumerate(winners):
            if idx < s:
                new_generation.append(Balloon(winner.gene.array))

        # new_generation.extend(winners[:s])

        # for balloon in new_generation:
        #     balloon.x = 25
        #     balloon.y = SH // 2
        #     balloon.won = False

        if winners:
            s = int((30 * population_size) / 100)
            for _ in range(s):
                parent1 = random.choice(winners[:10]).gene
                parent2 = random.choice(winners[:10]).gene
                child = parent1.crossover(parent2)
                child.mutation(mutation_rate=0.025)
                new_generation.append(Balloon(child.array))

            # s = int((60 * population_size) / 100)
            # for j in range(s):
            while len(new_generation) != population_size:
                parent1 = random.choice(gene_pool).gene
                parent2 = random.choice(gene_pool).gene
                child = parent1.crossover(parent2)
                child.mutation(mutation_rate=0.025)
                new_generation.append(Balloon(child.array))
        else:
            s = population_size
            for j in range(s):
                parent1 = random.choice(gene_pool).gene
                parent2 = random.choice(gene_pool).gene
                child = parent1.crossover(parent2)
                child.mutation(mutation_rate=0.025)
                new_generation.append(Balloon(child.array))

        balloon_population = new_generation

        # method 2
        # for balloon in balloon_population:
        #     if balloon.won:
        #         temp = balloon
        #         balloon_population.remove(temp)
        #         balloon_population.insert(0, temp)
        # MyList.insert(index_to_insert,MyList.pop(index_to_remove))

    frame_count = 0
    balloons_alive = population_size
    finished = False


class MovingEnemy(pg.Rect):
    def __init__(self, x, y, w, h, vel, direction, right_lim=0, left_lim=0, top_lim=0, bottom_lim=0):
        # Call the __init__ method of the parent class.
        super().__init__(x, y, w, h)
        self.vel = vel
        self.subsurface = pg.Surface((self.w, self.h))
        self.direction = direction
        self.right_lim = right_lim
        self.left_lim = left_lim
        self.top_lim = top_lim
        self.bottom_lim = bottom_lim

    def update(self):
        if self.direction == 'horizontal':
            self.x += self.vel
            if self.right > self.right_lim or self.left < self.left_lim:
                self.vel = -self.vel
        elif self.direction == 'vertical':
            self.y += self.vel
            if self.top > self.top_lim or self.bottom < self.bottom_lim:
                self.vel = -self.vel

    def draw(self):
        # IMAGE = pg.image.load('heli.png').convert()  # or .convert_alpha()
        # # Create a rect with the size of the image.
        # rect = IMAGE.get_rect()
        # rect.center = (200, 300)

        enemy_image = pg.image.load('images/ghost.png')
        enemy_image = pg.transform.scale(enemy_image, (30, 30))
        SC.blit(enemy_image, (int(self.x), int(self.y)))
        # pg.draw.rect(SC, (255, 0, 0), (self.x, self.y, self.width, self.height))


class Coin(pg.Rect):
    def __init__(self, x, y, width, height):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.subsurface = pg.Surface((self.width, self.height))
        self.image = pg.image.load('images/coin.png')
        self.image = pg.transform.scale(self.image, (25, 25))

    def draw(self):
        SC.blit(self.image, (int(self.x), int(self.y)))

    # def update(self):
    #     if self.crashed:
    #         self.image = pg.image.load('shines.png')
    #         self.image = pg.transform.scale(self.image, (25, 25))
    #         SC.blit(self.image, (self.x, self.y))
    #
    #         self.image = pg.image.load('coin.png')
    #         self.image = pg.transform.scale(self.image, (25, 25))
    #         SC.blit(self.image, (self.x, self.y))
    #
    #         self.crashed = False


walls = [
    Obstacle(0, 0, 20, 720),
    Obstacle(100, 0, 20, 300),
    Obstacle(100, 420, 20, 300),
    Obstacle(100, 225, 200, 20),
    Obstacle(300, 75, 20, 170),
    Obstacle(450, 0, 20, 400),
    Obstacle(300, 300, 20, 330),
    Obstacle(300, 540, 750, 20),
    Obstacle(650, 300, 20, 330),
    Obstacle(450, 160, 700, 20),
    Obstacle(850, 300, 20, 240),
    Obstacle(850, 300, 430, 20),
    Obstacle(1040, 430, 440, 20),
    Obstacle(20, 700, 1280, 20),
    Obstacle(20, 0, 1280, 20),
    Obstacle(1260, 0, 20, 720),
    Obstacle(475, 630, 20, 90),
    Obstacle(825, 630, 20, 90),
    Obstacle(1080, 630, 200, 20)
]

vel_left = 4
vel_right = -4

moving_enemies = [
    MovingEnemy(500, 80, 30, 30, vel_right, 'horizontal', right_lim=1100, left_lim=500),
    MovingEnemy(500, 250, 30, 30, vel_right, 'vertical', top_lim=450, bottom_lim=250),
    MovingEnemy(900, 375, 30, 30, vel_right, 'vertical', top_lim=475, bottom_lim=375)
]

coins = [
    Coin(100, 350, 30, 30),
    Coin(200, 150, 30, 30),
    Coin(330, 590, 30, 30),
    Coin(530, 590, 30, 30),
    Coin(730, 590, 30, 30),
    Coin(930, 590, 30, 30)
]

level3 = {'walls': walls, 'moving_enemies': moving_enemies, 'coins': coins, 'move_limit': 1300}  # 1800

moving_enemies = [
    MovingEnemy(650, (720 / 2) - 70, 30, 30, vel_right, 'vertical', top_lim=620, bottom_lim=100),
    MovingEnemy(950, (720 / 2) + 90, 30, 30, vel_right, 'vertical', top_lim=620, bottom_lim=100)
]

coins = [
    Coin(100, 200, 30, 30),
    Coin(350, 720 / 2, 30, 30),
    Coin(650, 720 / 2, 30, 30),
    Coin(950, 720 / 2, 30, 30)
]

walls = [
    Obstacle(0, 0, 20, 720),
    Obstacle(20, 700, 1280, 20),
    Obstacle(20, 0, 1280, 20),
    Obstacle(1260, 0, 20, 720),
    Obstacle(200, 100, 20, 620),
    Obstacle(500, 0, 20, 380),
    Obstacle(500, 530, 20, 190),
    Obstacle(800, 300, 20, 420),
    Obstacle(800, 0, 20, 200),
    Obstacle(1100, 0, 20, 350),
    Obstacle(1100, 450, 20, 270)
]

level2 = {'walls': walls, 'moving_enemies': moving_enemies, 'coins': coins, 'move_limit': 700}

moving_enemies = [
    MovingEnemy(725, (720 / 2) - 70, 30, 30, vel_right, 'vertical', top_lim=620, bottom_lim=100),
    MovingEnemy(400, 135, 30, 30, vel_right, 'horizontal', right_lim=600, left_lim=350)
]

coins = [
    # Coin(100, 200, 30, 30),
    Coin(120, 500, 30, 30),
    Coin(475, 335, 30, 30),
    Coin(475, 135, 30, 30),
    Coin(900, 420, 30, 30)
]

walls = [
    Obstacle(300, 0, 20, 400),
    Obstacle(120, 400, 200, 20),
    Obstacle(500, 420, 20, 300),
    Obstacle(500, 420, 150, 20),
    Obstacle(450, 250, 220, 20),
    Obstacle(650, 0, 20, 250),
    Obstacle(800, 0, 20, 370),
    Obstacle(780, 470, 20, 250),
    Obstacle(800, 370, 300, 20),
    Obstacle(800, 470, 300, 20),
    Obstacle(100, 600, 20, 120),
    Obstacle(120, 600, 200, 20),
]

level1 = {'walls': walls, 'moving_enemies': moving_enemies, 'coins': coins, 'move_limit': 600}

levels = {'Level 1': level1, 'Level 2': level2, 'Level 3': level3}


def onsubmit():
    global gen_nb
    global level_nb
    gen_nb = int(gen_nb_box.get())
    level_nb = int(level_nb_box.get())
    window.quit()
    window.destroy()


window = Tk()
window.geometry('350x100')
label0 = Label(window, text='Enter the number of generations: ')
gen_nb_box = Entry(window)
label1 = Label(window, text='Enter the level to be played: ')
level_nb_box = Entry(window)
submit = Button(window, text='Submit', command=onsubmit)
window.update()

submit.grid(columnspan=2, row=3)
gen_nb_box.grid(row=0, column=1, pady=3)
label0.grid(row=0, pady=3)
level_nb_box.grid(row=1, column=1, pady=3)
label1.grid(row=1, pady=3)


while True:
    window.mainloop()
    level = 'Level ' + str(level_nb)
    move_limit = levels[level]['move_limit']
    clock.tick(FPS)
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit()

    counter_text = "Frame: " + str(frame_count)
    counter_limit_text = " / " + str(move_limit)

    # Fill the screen with the color (51, 51, 51)
    # SC.fill((51, 51, 51))
    SC.blit(background, (0, 0))

    current_level = levels[level]
    for wall in current_level['walls']:
        wall.draw()

    for enemy in current_level['moving_enemies']:
        enemy.draw()
        enemy.update()

    for coin in current_level['coins']:
        coin.draw()

    for balloon in balloon_population:
        balloon.draw()
        if balloon.alive:
            balloon.check_wall_collision(current_level['walls'])
            balloon.check_enemy_collision(current_level['moving_enemies'])
            balloon.check_boundary_collision()
            balloon.check_coin_collision(current_level['coins'])
            balloon.update()

    show_text(counter_text, 10, 30)
    show_text(counter_limit_text, 160, 33, 30)
    show_text("Generation: " + str(generation_count), 10, 80)
    show_text("Alive balloons: " + str(balloons_alive), 10, 110, 30)
    show_text("Last gen:", 10, 550, 45)  # .
    show_text("Total balloons:             " + str(len(balloon_population)), 30, 590, 25)
    show_text("Successful balloons:   " + str(success_count), 30, 610, 25)
    if success_count_diff > 0:
        show_text("+" + str(success_count_diff), 250, 610, 25, pg.Color("green"))
    else:
        show_text("-" + str(-success_count_diff), 250, 610, 25, pg.Color("red"))

    show_text("Avg. fitness:            " + str(round(avg_fitness, 3)), 30, 630, 25)
    if avg_fitness_diff > 0:
        show_text("+" + str(round(avg_fitness_diff, 3)), 250, 630, 25, pg.Color("green"))
    else:
        show_text("-" + str(round(-avg_fitness_diff, 3)), 250, 630, 25, pg.Color("red"))

    show_text("Record time :           " + str(lowest_time), 30, 650, 25)
    if lowest_time_diff > 0:
        show_text("+" + str(lowest_time_diff), 250, 650, 25, pg.Color("red"))
    else:
        show_text("-" + str(-lowest_time_diff), 250, 650, 25, pg.Color("green"))

    show_text(str(level), 550, 20, 80, level_color)
    # if levelCount == 5:
    #     show_text("FINAL", 604, 80, 40, levelColor)

    finish_image = pg.image.load('images/goal.png')
    finish_image = pg.transform.scale(finish_image, (45, 45))
    SC.blit(finish_image, (int(finish.x), int(finish.y)))
    # pg.draw.circle(SC, pg.Color("green"), (int(finish.x), int(finish.y)), 20

    pg.display.update()

    if frame_count >= move_limit - 1 or balloons_alive <= 0:
        frame_count = move_limit - 1
        finished = True
    else:
        frame_count += 1

    if finished:
        finish_generation()
