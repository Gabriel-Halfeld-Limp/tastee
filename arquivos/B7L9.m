 % TITLE                                                                       
 % ****   A 6 Bus Test System  ****  
 
%Bus Data
% NB  T G  VT    Angle    PG     QG       QMIN   QMAX   PLOAD    QLOAD   QBAR 
 DBAR = [
   1 2 1 1.0     0.0     1.0     6.9      -9999  9999.0    0.0    0.0        0.0
   2 0 0 1.0   -4.98     0.0    0.00      0.0    0.0       20.0   8.5     0.0 
   3 1 1 1.0   -12.72    0.0    0.00     -200.0  250.0     40.0   17.0     0.0
   4 1 1 1.0    0.0      0.0    0.00     -200.0  250.0     30.0     4.0       0.0
   5 0 0 1.0    -4.98    0.0    0.00      0.0    0.0       30.0   12.7     0.0 
   6 0 0 1.0   -10.72    0.0    0.00      0.0    0.0       40.0   17.3     0.0
   7 0 0 1.0   -12.72    0.0    0.00      0.0    0.0       5.0     1.3     0.0];

% Line Data
% From  T0    r         x       Bsh                            Flow-Limit 
 DLIN = [
   1    2    1    10    0.0    0.0      0.000    0.000   0.0  15.0    0.0
   2    3    2    17    0.0    0.0      0.000    0.000   0.0  15.0    0.0
   3    4    5    10    0.0    0.0      0.000    0.000   0.0  10.0    0.0
   4    5    1    15    0.0    0.0      0.000    0.000   0.0  25.0    0.0
   5    6    2    18    0.0    0.0      0.000    0.000   0.0  20.0    0.0
   3    6    3    13    0.0    0.0      0.000    0.000   0.0  30.0    0.0
   1    5    1    14    0.0    0.0      0.000    0.000   0.0  30.0    0.0
   5    7    2    13    0.0    0.0      0.000    0.000   0.0  40.0    0.0
   4    2    2    12    0.0    0.0      0.000    0.000   0.0  20.0    0.0];

% Dados para Limites de Circuitos - DVIO

DVIO = 1.05*[1 15.00
        2 15.00
        3 10.00
        4 25.00
        5 20.00
        6 30.00
        7 30.00
        8 40.00
        9 60.00];
    
    DLIN(:,10) = DVIO(:,2);
    


% Choose the lower and upper limits of voltage
DTEN = [
    0  0.80  1.20
    1  1.00  1.05
];

% Active Power Generation Data
% Bus   PGmin  PGmax       Cost($/Mwh)
DGER = [ 
   1     0.0   60           10.     0     0 
   3     0.0   80           20.     0     0
   4     0.0   70           30.     0     0];

% % Choose the Limit of powerflow
% FLG_LIM = 1; % Considerar limite de LT
% FLG_LIM = 0; % Não Considerar limite de LT

FLG_LIM = 1;

% % Choose the Objective Function
% 
 OBJF = 2;   % Choose OBJF = 1 for minimal operational cost 
%            % Choose OBJF = 2 for minimal transmission losses
%            
% % Choose number 1 to PrntScr 
% 
 R_BAR = 1;   % R_BAR = 1; Imprime Relatório de Barra 
%             % R_BAR = 0; Não Imprime Relatório de Barra 
% 
 R_GER = 1;   % R_GER = 1; Imprime Relatório de Geração 
%             % R_GER = 0; Não Imprime Relatório de Geração 
% 
 R_LIN = 1;   % R_BAR = 1; Imprime Relatório de Linha 
%             % R_BAR = 0; Não Imprime Relatório de Linha 
         
           
           