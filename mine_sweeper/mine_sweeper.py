import os
import random
import math
import asyncio

from  PIL  import   Image, ImageFont, ImageDraw
from hoshino.typing import CQEvent
from hoshino import R, Service, priv, log

FILE_PATH = os.path.dirname(__file__)

sv = Service('mine_sweeper', manage_priv=priv.SUPERUSER, enable_on_default=True, visible=False)
logger = log.new_logger('mine_sweeper')

IMAGE_PATH = R.img('mine_sweeper').path
if not os.path.exists(IMAGE_PATH):
	os.mkdir(IMAGE_PATH)
	logger.info('create folder succeed')

###显示###
NOTCLICK = 0		#未点击
ALREADY_CLICK = -1	#已点击，且附近无雷
FLAG = -2			#标记
MAYBE = -3			#可能

###判定###
NOT_MINE = 0		#无雷
HAVE_MINE = 1		#有雷

###显示偏移###
OFFSET_X = 30		#整体右移
OFFSET_Y = 20		#整体下移

###常用颜色###
COLOR_BLACK = (0,0,0)
COLOR_WRITE = (255,255,255)
COLOR_RED = (255,0,0)
COLOR_DEFAULT = (50, 150, 250)	#未开启的雷区默认颜色

###胜负判断###
WIN = 1
NORMAL = 0
LOSE = -1
TIME_OUT = -2


#扫雷
class MineSweeper:
	#初始化
	def __init__(self, gid, manager, vertical_range_x, across_range_y, mine_num, grid_size = 30) -> None:
		self.gid = gid
		self.mgr = manager
		self.end_flag = NORMAL		#结束标记
		self.first_click = False	#是否是第一次点击
		self.mine_corr = []			#保存有雷的坐标
		self.win_condition = 0		#胜利条件，用来保存已打开的格子数量，总格子数量 - 已打开格子数量 == 地雷数量 

		self.grid_size = grid_size	#格子尺寸
		self.vertical_range_x = vertical_range_x
		self.across_range_y = across_range_y
		self.mine_num = mine_num	#地雷数量

		width = (self.vertical_range_x + 2) * self.grid_size
		hight = (self.across_range_y + 2) * self.grid_size

		#雷区显示 0为未点击，-1为已点击，-2为标记，其它数字为附近有多少个雷
		self.mine_field_display = [[NOTCLICK for i in range(self.across_range_y)] for j in range(self.vertical_range_x)]
		#雷区判定 0为无雷，1为有雷
		self.mine_field_judge = [[NOT_MINE for i in range(self.across_range_y)] for j in range(self.vertical_range_x)]

		self.im = Image.new("RGB", (width, hight), COLOR_WRITE)
		self.draw = ImageDraw.Draw(self.im)
		FONTS_PATH = os.path.join(FILE_PATH,'fonts')
		FONTS = os.path.join(FONTS_PATH,'msyh.ttf')
		self.font = ImageFont.truetype(FONTS, 15)
		self.textFont = ImageFont.truetype(FONTS, 22)


	def __enter__(self):
		self.mgr.playing[self.gid] = self
		self.drawGrid()
		return self
	def __exit__(self, type_, value, trace):
		del self.mgr.playing[self.gid]


	#雷区判定初始化，随机在格子内放进地雷
	def judgeInit(self, no_mine):
		arr = [i for i in range( self.vertical_range_x * self.across_range_y )]
		arr.remove(no_mine)
		ranArr = random.sample(arr, self.mine_num)
		for mine in ranArr :
			x = math.floor(mine / self.across_range_y)
			y = mine % self.across_range_y
			self.mine_field_judge[x][y] = HAVE_MINE
			self.mine_corr.append( (x, y) )

	#雷区点击判定
	def judgeClick(self, click_x, click_y):
		if self.mine_field_display[click_x][click_y] != NOTCLICK:
			return
		if not self.first_click :#点击第一下一定不会爆炸
			self.judgeInit(click_x * self.across_range_y + click_y)
			self.first_click = True

		if self.mine_field_judge[click_x][click_y] != HAVE_MINE:
			self.win_condition += 1
			null_grid_coor = []	#保存被点击的格子附近的空格子坐标
			continue_num = 0 #保存跳过的格子，用来计算边缘
			for i in range(3):
				for j in range(3):
					scan_x = click_x-1+i
					scan_y = click_y-1+j
					if ( scan_x < 0 or scan_y < 0 or scan_x >= self.vertical_range_x or scan_y >= self.across_range_y
						or (i == 1 and j == 1) ):
						continue_num += 1
						continue
					
					if self.mine_field_judge[scan_x][scan_y] == HAVE_MINE:
						self.mine_field_display[click_x][click_y] += 1
					else:
						if ((scan_x, scan_y) not in null_grid_coor):
							null_grid_coor.append( (scan_x, scan_y) )

			if len(null_grid_coor) >= 9 - continue_num:
				self.mine_field_display[click_x][click_y] = ALREADY_CLICK
				self.fillGrid(click_x, click_y, COLOR_WRITE)
				for coor in null_grid_coor :
					if self.mine_field_display[coor[0]][coor[1]] == NOTCLICK :
						self.judgeClick(coor[0], coor[1])		#递归消除
			else:
				show_num = ""
				if self.mine_field_display[click_x][click_y] > 0 :
					show_num = str(self.mine_field_display[click_x][click_y])
				self.fillGrid(click_x, click_y, COLOR_WRITE, COLOR_BLACK, text = show_num)
			
			if self.vertical_range_x  * self.across_range_y  - self.win_condition == self.mine_num :
				self.end_flag = WIN
				return WIN
			return NORMAL
		else:
			self.fillGrid(click_x, click_y, COLOR_RED)
			self.end_flag = LOSE
			return LOSE

	#检查坐标合法性
	def checkCoor(self, grid_x, grid_y):
		if (grid_x < 0 or grid_y < 0 
			or grid_x > self.vertical_range_x 
			or grid_y > self.across_range_y):
			return False
		return True

	#设置有雷标记
	def setFlag(self, grid_x, grid_y):
		if self.mine_field_display[grid_x][grid_y] == NOTCLICK:
			self.mine_field_display[grid_x][grid_y] = FLAG
			self.fillGrid(grid_x, grid_y, COLOR_DEFAULT, textColor = COLOR_RED, text = '！')
			return True
		elif self.mine_field_display[grid_x][grid_y] == FLAG:
			self.mine_field_display[grid_x][grid_y] = NOTCLICK
			self.fillGrid(grid_x, grid_y, COLOR_DEFAULT)
			return True
		return False
	#设置可能有雷标记
	def setMaybe(self, grid_x, grid_y):
		if self.mine_field_display[grid_x][grid_y] == NOTCLICK:
			self.mine_field_display[grid_x][grid_y] = MAYBE
			self.fillGrid(grid_x, grid_y, COLOR_DEFAULT, textColor = COLOR_RED, text = '？')
			return True
		elif self.mine_field_display[grid_x][grid_y] == MAYBE:
			self.mine_field_display[grid_x][grid_y] = NOTCLICK
			self.fillGrid(grid_x, grid_y, COLOR_DEFAULT)
			return True
		return False

	#获取图片
	def getImage(self):
		return self.im

	#获取地雷图片
	def getMineImage(self):
		for corr in self.mine_corr:
			self.fillGrid(corr[0], corr[1], COLOR_RED)
		return self.im

	#画格子，初始化整个雷区显示
	def drawGrid(self):
		j = 0
		for i in range(self.across_range_y + 1) : #画横线 上往下画
			self.draw.line( (0 + OFFSET_X, j + OFFSET_Y) + (self.grid_size * self.vertical_range_x + OFFSET_X, j + OFFSET_Y), fill = COLOR_BLACK, width = 2 )
			if i != self.across_range_y : #坐标标记
				#右边的坐标标记
				self.draw.text((self.grid_size * self.vertical_range_x + 5 + OFFSET_X, j + self.grid_size/3 - 3 + OFFSET_Y), str(i+1), font = self.font, fill = COLOR_BLACK)
				if i + 1 >= 10: #坐标标记是两位数时，偏移要大一点
					#左边的坐标标记
					self.draw.text((0 + OFFSET_X - 20, j + self.grid_size/3 - 3 + OFFSET_Y), str(i+1), font = self.font, fill = COLOR_BLACK)
				else:
					#左边的坐标标记
					self.draw.text((0 + OFFSET_X - 12, j + self.grid_size/3 - 3 + OFFSET_Y), str(i+1), font = self.font, fill = COLOR_BLACK)
			j += self.grid_size
		j = 0
		for i in range(self.vertical_range_x + 1) : #画竖线 左往右画
			self.draw.line( (j + OFFSET_X, 0 + OFFSET_Y) + (j + OFFSET_X, self.grid_size * self.across_range_y + OFFSET_Y), fill = COLOR_BLACK, width = 2 )
			if i != self.vertical_range_x :	#坐标标记
				if i + 1 >= 10: #坐标标记是两位数时，偏移稍微不同
					#上边的坐标标记
					self.draw.text((self.grid_size/3-4 + j + OFFSET_X, self.grid_size * self.across_range_y + OFFSET_Y), str(i+1), font = self.font, fill = COLOR_BLACK)
					#下边的坐标标记
					self.draw.text((self.grid_size/3-4 + j + OFFSET_X, OFFSET_Y - 18), str(i+1), font = self.font, fill = COLOR_BLACK)
				else:
					#上边的坐标标记
					self.draw.text((self.grid_size/2-4 + j + OFFSET_X, self.grid_size * self.across_range_y + OFFSET_Y), str(i+1), font = self.font, fill = COLOR_BLACK)
					#下边的坐标标记
					self.draw.text((self.grid_size/2-4 + j + OFFSET_X, OFFSET_Y - 18), str(i+1), font = self.font, fill = COLOR_BLACK)
			j += self.grid_size
		self.fillAllGrid()	#填充

	#填充所有格子到默认状态
	def fillAllGrid(self,):
		for x in range(self.vertical_range_x) : #填充
			for y in range(self.across_range_y):
				self.fillGrid(x, y, COLOR_DEFAULT)

	#填充格子，可填充底色、文字
	def fillGrid(self, grid_x, grid_y, back_color, textColor = COLOR_BLACK, text = ''):
		self.draw.rectangle( (2 + grid_x * self.grid_size + OFFSET_X, 2 + grid_y * self.grid_size + OFFSET_Y, 
							  self.grid_size - 1 + grid_x * self.grid_size + OFFSET_X, self.grid_size - 1 + grid_y * self.grid_size +OFFSET_Y), 
							  fill = back_color )
		self.draw.text( ( 9 + grid_x * self.grid_size + OFFSET_X, 1 + grid_y * self.grid_size + OFFSET_Y), text, font = self.textFont, fill = textColor)

#管理器
class manager:
	def __init__(self):
		self.playing = {}

	def is_playing(self, gid):
		return gid in self.playing

	def start(self, gid, grid_x, grid_y, mine_num):
		return MineSweeper(gid, self, grid_x, grid_y, mine_num)

	def get_game(self, gid):
		return self.playing[gid] if gid in self.playing else None

mgr = manager()
DURATION = 1
WAIT_TIME = 3

MAX_X = 30	#最大值
MAX_Y = 30	#最大值

####难度####
DEGREE_EASY_X = 8
DEGREE_EASY_Y = 8
DEGREE_EASY_MINE_NUM = 5
DEGREE_EASY_TIME = 5

DEGREE_NORMAL_X = 10
DEGREE_NORMAL_Y = 10
DEGREE_NORMAL_MINE_NUM = 15
DEGREE_NORMAL_TIME = 10

DEGREE_HARD_X = 15
DEGREE_HARD_Y = 15
DEGREE_HARD_MINE_NUM = 30
DEGREE_HARD_TIME = 10


@sv.on_rex(r'^扫雷( |)(?:(((\d+)(X|x|×)(\d+))|(简单|普通|困难)))? *( |)? *(\d+)? *(\d+)?')
async def mine_sweeper(bot, ev):

	if mgr.is_playing(ev.group_id):
		await bot.finish(ev, "游戏仍在进行中…")

	match = ev['match']
	if not match:
		return
	
	grid_x = DEGREE_EASY_X
	grid_y = DEGREE_EASY_Y
	mine_num = DEGREE_EASY_MINE_NUM
	time_min = DEGREE_EASY_TIME
	degree_text = "简单"

	degree = match.group(2)
	if degree == '简单':
		pass
	elif degree == '普通':
		grid_x = DEGREE_NORMAL_X
		grid_y = DEGREE_NORMAL_Y
		mine_num = DEGREE_NORMAL_MINE_NUM
		time_min = DEGREE_NORMAL_TIME
		degree_text = degree
	elif degree == '困难':
		grid_x = DEGREE_HARD_X
		grid_y = DEGREE_HARD_Y
		mine_num = DEGREE_HARD_MINE_NUM
		time_min = DEGREE_HARD_TIME
		degree_text = degree
	elif not degree :
		pass
	else:
		if match.group(4) : grid_x = int(match.group(4))
		if match.group(6) : grid_y = int(match.group(6))
		if match.group(9) : mine_num = int(match.group(9))
		if match.group(10) : time_min = int(match.group(10))
		degree_text = "自定义"

	if (grid_x <= 2 or grid_y <= 2 or mine_num <= 2 or grid_x * grid_y <= mine_num):
		await bot.send(ev, '参数错误，最小为雷区边长不能小于3，地雷数量不能大于或等于雷区格子数量', at_sender=True)
		return
	if grid_x > MAX_X or grid_y > MAX_Y:
		await bot.send(ev, '超过最大值', at_sender=True)
		return

	image_path = R.img(f'{IMAGE_PATH}/{ev.group_id}.jpg').path
	if os.path.exists(image_path):
		os.remove(image_path)

	with mgr.start(ev.group_id, grid_x, grid_y, mine_num) as ms:
		img = ms.getImage()
		img.save(image_path)
		await bot.send(ev, f"扫雷游戏即将开始，当前难度为“{degree_text}”，雷区大小为{grid_x}x{grid_y}，共有{mine_num}个地雷，游戏持续{time_min}分钟")
		await asyncio.sleep(WAIT_TIME)
		await bot.send(ev, R.img(image_path).cqcode)
		for i in range(math.floor(time_min * 60 / WAIT_TIME)):
			await asyncio.sleep(WAIT_TIME)
			if ms.end_flag != NORMAL:
				break
		img = ms.getMineImage()
		img.save(image_path)
		msg = []
		if ms.end_flag == LOSE :
			msg.append(f"很可惜，您踩到了地雷，游戏结束。\n最终结果：\n{R.img(image_path).cqcode}")
		elif ms.end_flag == WIN:
			msg.append(f"恭喜，你已成功找出所有地雷！\n最终结果：\n{R.img(image_path).cqcode}")
		else:
			msg.append(f"很可惜，您没有在规定时间内扫雷成功，游戏结束。\n最终结果：\n{R.img(image_path).cqcode}")
		await bot.send(ev, "\n".join(msg))


@sv.on_rex(r'^(\d+)(,|，|.)(\d+)')
async def click_grid(bot, ev: CQEvent):
	match = ev['match']
	if not match :
		return
	gid = ev.group_id
	uid = ev.user_id
	grid_x = int(match.group(1))
	grid_y = int(match.group(3))
	ms = mgr.get_game(gid)
	if not ms  or ms.end_flag != NORMAL:
		return
	if not ms.checkCoor(grid_x, grid_y):
		await bot.send(ev, '坐标错误', at_sender=True)
		return
	
	image_path = R.img(f'{IMAGE_PATH}/{gid}.jpg').path
	
	ret = ms.judgeClick(grid_x - 1, grid_y - 1)
	img = ms.getImage()
	img.save(image_path)
	if ret == WIN or ret == LOSE :
		await bot.send(ev, f"游戏结束，请等待结算\n{R.img(image_path).cqcode}")
	elif ret == NORMAL :
		await bot.send(ev, R.img(image_path).cqcode)

@sv.on_rex(r'^(可能|未知|？|\?|标记|！|!)(\d+)(,|，|.)(\d+)')
async def click_flag(bot, ev: CQEvent):
	match = ev['match']
	if not match :
		return
	gid = ev.group_id
	ms = mgr.get_game(gid)
	if not ms  or ms.end_flag != NORMAL:
		return
	
	operation = match.group(1)
	grid_x = int(match.group(2))
	grid_y = int(match.group(4))
	if not ms.checkCoor(grid_x, grid_y):
		await bot.send(ev, '坐标错误', at_sender=True)
		return
	
	image_path = R.img(f'{IMAGE_PATH}/{gid}.jpg').path
	
	ret = False
	if operation == "可能" or operation == "未知" or operation == "？" or operation == "?":
		ret = ms.setMaybe(grid_x - 1, grid_y - 1)
	elif operation == "标记" or operation == "！" or operation == "!":
		ret = ms.setFlag(grid_x - 1, grid_y - 1)
	if not ret : return
	img = ms.getImage()
	img.save(image_path)
	await bot.send(ev, R.img(image_path).cqcode)


@sv.on_fullmatch(("扫雷结束","结束扫雷"))
async def game_finish(bot, ev: CQEvent):
	if not priv.check_priv(ev, priv.ADMIN):
		await bot.finish(ev, '只有群管理才能强制结束', at_sender=True)
	ms = mgr.get_game(ev.group_id)
	if not ms  or ms.end_flag:
		return
	ms.end_flag = LOSE
	await bot.send(ev, f"您已强制结束扫雷，请等待结算")

@sv.on_fullmatch(("查看雷区"))
async def game_finish(bot, ev: CQEvent):
	if not priv.check_priv(ev, priv.SUPERUSER):
		await bot.finish(ev, '只有机器人管理者才能查看雷区', at_sender=True)
	ms = mgr.get_game(ev.group_id)
	if not ms  or ms.end_flag:
		return
	msg = ""
	for corr in ms.mine_corr :
		msg += ("(" + str(corr[0] + 1) + "," + str(corr[1] + 1) + ")")
	await bot.send(ev, msg)

@sv.on_fullmatch(("扫雷帮助"))
async def game_finish(bot, ev: CQEvent):
	msg = '''	《扫雷帮助》
~~目前有3个默认难度：简单、普通、困难~~
~~扫雷游戏所有群员都可参与(不要捣乱哦)~~
~~通关默认难度，所有参与者都可获得贵族金币~~
一、游戏开启：
1、扫雷
可快速开始简单难度的扫雷游戏
2、扫雷(难度)
	如：扫雷 普通
即可开始普通难度的扫雷游戏
3、扫雷(雷区大小)(地雷数量)(持续时间/分钟)
	如：扫雷 10x10 5 1
即可开启10x10大小，有5个雷，
持续1分钟的自定义扫雷游戏。
注意：雷区边长不能小于3，
地雷数量不能大于或等于雷区格子数量。
二、游戏开启后：
1、(横坐标),(纵坐标)
	如：2，3
点击了第2列第3行的格子(逗号可用.代替)
2、标记/!(横坐标),(纵坐标)
	如：标记2，3 或 !2,3
标记第2列第3行的格子有地雷
再次发送则取消
3、可能/未知/?(横坐标),(纵坐标)
	如：可能2，3 或 ?2,3
标记第2列第3行的格子可能有地雷
再次发送则取消
4、结束扫雷
强制结束游戏，只有管理员可以使用'''
	await bot.send(ev, msg)
