
       %barra   tipo                        carga 
DBAR=[   1       2     0  0  0  0  0  0  0  0;
         2       0     0  0  0  0  0  0  0  0;
         3       0     0  0  0  0  0  0  0 10.0];


      %p  q   R    X               cap
 DLIN=[1  2  10   100    0 0 0 0 0   2;
       1  3  15   100    0 0 0 0 0   10;
       2  3  5    50     0 0 0 0 0   10];

         %barra prod.min  prod.max    custo
DGER=[     1       0        15         10;
           2       0        15         20;
           3       0        15         400];
              