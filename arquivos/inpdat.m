%-------------------------------------------------------------
%------------ Subrotina para entrada de dados-----------------
%-------------------------------------------------------------


function inpdat

% barra
global DBAR NBAR PLOAD ANGLE BREF
% linha
global DLIN NLIN SB EB r x G B Bor FLIM 
global SIG NCV NCVCIR NCIRCV 
global fij fji
% gerador
global DGER NGER BARPG PGMIN PGMAX CPG
% constantes gerais
global PB NITER PAREI DIFMAX TOL
% PL
global CX Aeq Beq Aiq Biq Vub Vlb NVAR NCAeq NLAeq NLBeq


%----------Dados das barras----------

[NBAR,AUX]=size(DBAR);
FC = 1;
for i=1:NBAR
   PLOAD(i)=FC*DBAR(i,10)/100;
   TIPO(i) = DBAR(i,2);
   if TIPO(i) == 2
       BREF = i;
   end
end


%----------Dados das linhas----------

[NLIN,AUX]=size(DLIN);

for i=1:NLIN
   SB(i)  = DLIN(i,1); %Vetor da barra de partida (STARTBUS)
   EB(i)  = DLIN(i,2); %Vetor da barra de chegada (ENDBUS);
   r(i)   = DLIN(i,3)/100; % resistência série
   x(i)   = DLIN(i,4)/100; % reatância série
   G(i)   = r(i)/(r(i)^2+x(i)^2); % condutância série
   B(i)   = x(i)/(r(i)^2+x(i)^2); % susceptância
   
   Bor(i) = 1/x(i); % susceptância série (gamma)
   FLIM(i)=DLIN(i,10)/100; %Fluxo limite em pu-MW
end


%----------Dados dos geradores----------

[NGER,AUX]=size(DGER);

for i=1:NGER
   BARPG(i) = DGER(i,1); % Apontador barra/gerador. BARPG(2)=4 significa BAR do GER 2 é 4
   PGMIN(i) = DGER(i,2)/PB;
   PGMAX(i) = DGER(i,3)/PB;
   CPG(i)   = DGER(i,4); % Custo operacional do gerador
end



%Inicializando variáveis

NVAR = NGER + NBAR; %Número de variáveis

