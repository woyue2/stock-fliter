```
{ VOLUP X YANG X SHIPAN 主板精选版(上沿突破增强) }

{ 1. 基础定义 }
V_MA20 := MA(VOL, 20);
HIGH_250 := HHV(H, 250);
MAX_OC := MAX(C, O);
MIN_OC := MIN(C, O);
UPPER_SHADOW := H - MAX_OC;
LOWER_SHADOW := MIN_OC - L;
BODY := ABS(C - O);
DAY_RANGE := MAX(H - L, 0.01);
PCT_CHG := (C - REF(C, 1)) / REF(C, 1) * 100;

{ 2. 试盘信号定义 }
LOW_POS := C < HIGH_250 * 0.8;
COND_LIMIT := LOW_POS AND PCT_CHG > 7.0 AND VOL > V_MA20 * 1.3;
COND_UPPER := LOW_POS AND (H-MAX_OC) > BODY * 1.5 AND (H-MAX_OC) > DAY_RANGE * 0.4 AND VOL > V_MA20 * 1.5;
COND_LOWER := LOW_POS AND (MIN_OC-L) > BODY * 1.5 AND VOL > V_MA20 * 1.1;
SHIPAN_COUNT := COUNT(COND_LIMIT OR COND_UPPER OR COND_LOWER, 45);

{ --- 板块过滤逻辑 --- }
IS_MAIN_BOARD := NOT(CODELIKE('30')) AND NOT(CODELIKE('68'));
NOT_ST := IF(NAMELIKE('ST'), 0, 1) AND IF(NAMELIKE('*ST'), 0, 1);

{ 3. 核心选股条件 }
{ 条件1: 昨日放量 (昨量 > 前3天每一天的量) }
YDAY_VOL_BREAK := REF(V, 1) > REF(V, 2) AND REF(V, 1) > REF(V, 3) AND REF(V, 1) > REF(V, 4);

{ 确认: 前天(第2天)的量小于昨天(第1天)的量 --- 证明昨天是真正的爆发 }
YDAY_VOL_STRONG := REF(V, 2) < REF(V, 1);

{ 条件2: 今日阳线 & 缩量 }
TODAY_YANG := C > O;
TODAY_VOL_LESS := V < REF(V, 1);

{ 条件3: 柱体中点递增 (中点 = (开+收)/2) }
MP0 := (C + O) / 2;           
MP1 := (REF(C,1) + REF(O,1)) / 2; 
MP2 := (REF(C,2) + REF(O,2)) / 2; 
CENTER_UP := MP0 > MP1 AND MP1 > MP2; 

{ 条件4: 柱体上沿突破 (今日实体顶部 > 昨日实体顶部) }
TOP_UP := MAX_OC > REF(MAX_OC, 1);

{ 4. 汇总判断 }
{ 整合：昨日爆发 + 今日缩量阳线 + 重心向上 + 实体顶突破 + 试盘历史 + 主板非ST }
IS_MATCH := YDAY_VOL_BREAK AND YDAY_VOL_STRONG AND TODAY_YANG AND TODAY_VOL_LESS AND CENTER_UP AND TOP_UP AND SHIPAN_COUNT >= 1 AND IS_MAIN_BOARD AND NOT_ST;

{ --- 计算排序比值 --- }
MAX_V3 := MAX(REF(V,2), MAX(REF(V,3), REF(V,4)));
昨三高比: IF(IS_MATCH, REF(V,1) / MAX_V3, 0);

```


@code_block  请用 数字2代表今天，数字1代表昨天，数字0代表前天，用纯文字 描述筛选条件
【量能条件】

第1天成交量，必须大于第0天、再前一天（-1天）、以及再前两天（-2天）的成交量 —— 第1天是近几天里量最大的一天，确认为真放量爆发
【今日形态条件】

第2天收盘价 > 开盘价 —— 第2天必须是阳线

第2天成交量 < 第1天成交量 —— 第2天比第1天缩量，说明不是追涨盘，而是主力控盘

【重心向上条件】

第2天K线实体中点 > 第1天K线实体中点 > 第0天K线实体中点 —— 三天的价格重心连续抬升，趋势向好
【实体顶部突破条件】

第2天实体顶部（开收中较高者）> 第1天实体顶部 —— 今天的多头实体已经往上突破了昨天实体的上边界，多头力量占据绝对主动
【试盘历史条件】

过去45天内，出现过至少1次试盘信号（三种信号任一满足即可）：
涨停试盘：股价低于250日高点八折，当日涨幅超7%，且成交量明显放大
上影试盘：股价低于250日高点八折，上影线长度超过实体1.5倍且超过日振幅40%，成交量明显放大
下影试盘：股价低于250日高点八折，下影线长度超过实体1.5倍，成交量小幅放大
【股票资质过滤】

代码不以30开头（排除创业板）
代码不以68开头（排除科创板）
股票名称中不含ST或*ST（排除风险股）
排序依据：以第1天成交量除以第0天、-1天、-2天中的最大成交量，得到"昨三高比"，数值越大说明昨日放量越强劲，排名越靠前。