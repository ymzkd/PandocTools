# Etherポートランド荷重計算
ASCE 7-20 に基づき、Etherポートランドの荷重を計算する。

## 風荷重計算
### 速度圧 $q_z$ の計算
Section 28.3.2より速度圧 $q_z$ の計算

$$
q_z = 0.00256 \cdot K_z \cdot K_{zt} \cdot K_d \cdot V^2 \quad \text{[Psf]} \tag{28.3-1}
$$

なおSI単位系の式も併記されていて、

$$
q_z = 0.613 K_z \cdot K_{zt} \cdot K_d V^2 \quad \text{[Pa]} \tag{28.3-1}
$$

#### $K_d$ : Wind Directionality Factor
Table 26.6-1 (Chimney, Round) section より $K_d = 0.95$

#### $K_z$ : Velocity Pressure Exposure Coefficients
Table 29.3-1 より高さ$h = 12.2 \text{ m}$とすると、Exposure factorやカテゴリは Section 26.7より判断でき、Surface Roughness B, Exposure B(都市部で高い建物に囲まれている)とすると、$K_z$の計算に必要なパラメータは以下のようにTable 26.9-1より求められ、
- $z_g = 365.76 \text{ m}$, $\alpha = 7.0$ [Table 26.9-1]
- $z_g = 274.32 \text{ m}$, $\alpha = 9.5$ [これはExposureをCとする場合]

$$
K_z = 2.01 \times \left(\frac{z}{z_g}\right)^{2/\alpha} = 2.01 \times \left(\frac{12.2}{365.75}\right)^{2/7} = 0.761 \quad \text{(1.044 : Cなら)}
$$

と得られる。

#### $K_{zt}$ : Topographic Factor(Section 26.8)
丘やその他の地形の影響により、$K_{zt} = 1.0$ とする。

#### $V$ : 基準風速
Section 26.5.1 により、Risk Category II において、MRI (再現期間) 700年を用いて、


$$
V = 43 \text{ m/s} \Rightarrow 96.2 \text{ mph}
$$

以上より速度圧 $q_z$ は、

$$
\begin{align*}
q_z &= 0.00256 \cdot K_z \cdot K_{zt} \cdot K_d \cdot V^2 \quad \text{[psf]} \\
&= 0.00256 \times 0.761 \times 1.0 \times 0.95 \times 96.2^2 \\
&= 17.13 \text{ [psf]} = 0.82 \text{ [kN/m}^2\text{]}
\end{align*}
$$

と求められる。

### 風圧力 $W$ の計算
Section 29.5 Design Wind Loads - Other Structureに基づく風圧力計算式は以下の通り。

$$
W = q_z \cdot G \cdot C_f \cdot A_f \quad \tag{29.5-1}
$$

ここで、

#### $G$ : Gust Effect Factor (Section 26.9)
Section 26.9.1 により、その他の構造物として、 $G = 0.85$

#### $C_f$ : 風力係数 (Fig29.5-1～Fig29.5-3)
Figure29.5-3の表面に凹凸のある煙突として、径が$D=150mm$程度、高さが$h=12.2m$なので、高さと径の比率は$h/D = 81.3$となり、表の中の最大値を取ることにすると、**Round** ($D/D_z > 2.5$), $h/D = 25$ **Very rough** として、風力係数は、
$$C_f = 1.2$$

以上より風圧力は

$$
W = q_z \cdot G \cdot C_f = 0.82 \times 0.85 \times 1.2 = 0.84 \text{ kN/m}^2
$$

となる。

## 地震力計算
水平震度 $C_s$ の計算は、Section 12.8.1 に基づき、

$$
C_s = \frac{S_{DS} \cdot I_e}{R} \tag{12.8-2}
$$

ここで、$I_e$は11.5.1で説明される重要度係数で、値としてはTable 1.5-2より設計クライテリアがRisk Category II の場合、$I_e = 1.0$ となる。
また、$R$は応答修正係数で、Table 15.4-2 P143(Section 15.6.3)より,構造物をAmusement Structuresとして、表から拾える。その他のパラメータも併記すると、
- $R = 2$, $\Omega_0 = 2$, $C_d = 2$

となる。それぞれのパラメータは以下のような意味を持つ。
- $R$: response modification coefficient  
- $C_d$: deflection amplification factor
- $\Omega_0$: overstrength factor

構造物の取り扱いをTable 15.4.2より,片持ち煙突(Welded Steel)としても計算する係数としては同じになる。

$C_s$の計算においては上限値が12.8.3式、12.8-4式で与えられており、下限値が12.8.5式、12.8-6式で与えられているため、合わせて参照する必要がある。

### 地震応答スペクトルパラメーター$S_{DS}$ および $S_{D1}$ の計算
設計加速度応答スペクトル$S_{DS}$ および一秒周期における応答スペクトル $S_{D1}$ を求める。
まず、設計場所によるパラメータ$S_s$と$S_1$は、Section 22のFigure 22-1～22-6より、Site Class Dとして、$S_s = 0.95$, $S_1 = 0.36$となる。
次にそれぞれTable 11.4.1, 11.4-2より、Site Coefficient $F_a = 1.12$, $F_v = 1.68$ と得られる。これより、

$$
S_{MS} = F_a S_s \tag{11.4-1} \Rightarrow S_{MS} = 1.064
$$

$$
S_{M1} = F_v S_1 \tag{11.4-2} \Rightarrow S_{M1} = 0.6048
$$

これを用いて、

$$
S_{DS} = \frac{2}{3} S_{MS} \tag{11.4.3} \Rightarrow S_{DS} = 0.7092
$$

$$
S_{D1} = \frac{2}{3} S_{M1} \tag{11.4.4} \Rightarrow S_{D1} = 0.4032
$$

#### $T_L$: Long period transition period
長周期成分をどの程度の周期まで考えておく必要があるかというパラメータであると思う。

Figure 22-12〜22-16の地図上プロットから敷地に該当するパラメータを取得し、$T_L = 16 \text{ sec}$とする。

#### $T_a$: 構造物の基本周期近似計算(Section 12.8.2.1)
生産によって固有周期を求めてもよいが、手間なので日本と同じように近似計算式で求めて良いとされている。

$$
T_a = C_t h_n^x \tag{12.8-7}
$$

Table 12.8-2 より：
- $C_t = 0.0488$ (All other structural system として, SI系計算パラメータである。)
- $x = 0.75$

構造高さ $h_n = 12.2 \text{ m}$ なので：

$$
T_a = 0.0488 \times 12.2^{0.75} = 0.3175 \text{ sec} = T
$$

これを構造物の固有周期とする。

### 水平震度 $C_s$ の最終計算
上限値や下限値を考慮して、最終的な水平震度 $C_s$ を求める。

#### $C_s$ の下限値

$$
\underline{C_s} = 0.044 S_{DS} I_e = 0.0312
$$

#### $C_s$ の上限値($T \leq T_L = 0.31 < 16$ の場合)

$$
\overline{C_s} = \frac{S_{D1}}{T(R/I_e)} = \frac{0.4032}{0.3185 \times (2/1.0)} = 0.6329
$$

#### $C_s$ の計算

$$
C_s = \frac{S_{DS}}{R} \cdot I_e = \frac{0.7093}{2} = 0.355
$$

これは、$\underline{C_s} \leq C_s \leq \overline{C_s}$で上限と下限にかからないためこの値が水平震度として利用できる。

### 地震力 $Q_E$ の算定
地震力は、以上で計算した水平震度$C_S$と構造物の重量$G$を用いて、

$$
Q_E = C_s \times G
$$

として計算できる。

$$
\int_V \mathbf{A}_2 \mathbf{A}_2^T dV = 
\begin{bmatrix}
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & \frac{6N_x}{5\ell} & 0 & -\frac{M_{yi}+M_{yj}}{2\ell} & 0 & \frac{N_x}{10} & 0 & -\frac{6N_x}{5\ell} & 0 & \frac{M_{yi}+M_{yj}}{2\ell} & 0 & \frac{N_x}{10} \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & -\frac{M_{yi}+M_{yj}}{2\ell} & 0 & \frac{N_x I_y}{A \cdot \ell^2} & 0 & 0 & 0 & \frac{M_{yi}+M_{yj}}{2\ell} & 0 & -\frac{N_x I_y}{A \cdot \ell^2} & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & \frac{N_x}{10} & 0 & 0 & 0 & \frac{2N_x \ell}{15} & 0 & -\frac{N_x}{10} & 0 & 0 & 0 & -\frac{N_x \ell}{30} \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & -\frac{6N_x}{5\ell} & 0 & \frac{M_{yi}+M_{yj}}{2\ell} & 0 & -\frac{N_x}{10} & 0 & \frac{6N_x}{5\ell} & 0 & -\frac{M_{yi}+M_{yj}}{2\ell} & 0 & -\frac{N_x}{10} \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & \frac{M_{yi}+M_{yj}}{2\ell} & 0 & -\frac{N_x I_y}{A \cdot \ell^2} & 0 & 0 & 0 & -\frac{M_{yi}+M_{yj}}{2\ell} & 0 & \frac{N_x I_y}{A \cdot \ell^2} & 0 & 0 \\
0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 & 0 \\
0 & \frac{N_x}{10} & 0 & 0 & 0 & -\frac{N_x \ell}{30} & 0 & -\frac{N_x}{10} & 0 & 0 & 0 & \frac{2N_x \ell}{15}
\end{bmatrix}
$$