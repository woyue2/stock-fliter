{量比×换手率×涨跌幅 选股公式}

{1.基础过滤: 排除停牌和ST股}
TP:=DYNAINFO(8)>0; {当日有成交量}
ST:=IF(NAMELIKE('S'),0,1) AND IF(NAMELIKE('*'),0,1);

{2.核心指标计算}
{量比: 当日成交量与过去5日平均成交量的比值}
{更精确的量比：分母为前5日均量，排除当日}
AVG5 := (REF(VOL,1)+REF(VOL,2)+REF(VOL,3)+REF(VOL,4)+REF(VOL,5)) / 5;
VR := VOL / AVG5;
VR_OK := VR > 4 AND VR < 10;


{涨跌幅: 3% 到 8%}
PCT := (C - REF(C, 1)) / REF(C, 1) * 100;
PCT_OK := PCT > 3 AND PCT < 8;

{价格: 必须大于 4 元}
PRICE_OK := C > 4;

{换手率: 2% 到 15%}
TURN_OK := HSL > 2 AND HSL < 15;

{成交金额: 2亿 到 20亿 (通达信 AMOUNT 单位为元)}
AMT_OK := AMOUNT > 200000000 AND AMOUNT < 2000000000;

{3.综合选股条件}
SELECT: TP AND ST AND VR_OK AND PCT_OK AND PRICE_OK AND TURN_OK AND AMT_OK;