# Arquitetura do sistema

Diagramas para a secção 9 do relatório ("Fluxograma ou diagrama do sistema"). Os blocos
`mermaid` aparecem desenhados no GitHub; para o relatório, abra-os em https://mermaid.live e
exporte como PNG.

## Módulos

```mermaid
flowchart LR
    subgraph UI["ui/ — interface (PySide6)"]
        MW[MainWindow<br/>menus, barras, cenas]
        CV[Canvas<br/>QOpenGLWidget]
        LP[Painel Camadas]
        PP[Painel Propriedades<br/>inspetor de matrizes]
        SS[Ecrã inicial animado]
        HS[Ajuda]
    end
    subgraph TOOLS["tools/ — ferramentas (Strategy)"]
        ST[Seleção / transformação]
        SH[Formas por arrasto]
        PT[Polígono · Mão livre · Mão]
    end
    CTL[controller.py<br/>estado + comandos + sinais]
    subgraph CORE["core/ — modelo (sem Qt/OpenGL)"]
        MX[matrix.py]
        GE[geometry.py]
        SHP[shapes.py]
        DOC[document.py]
        OPS[operations.py]
        HIS[history.py]
        FIO[fileio.py]
        ANI[animation.py]
        PICK[picking.py]
    end
    subgraph RENDER["render/ — OpenGL"]
        RD[renderer.py]
        CAM[camera.py]
        TES[tessellation.py]
        TEX[textures.py]
        EXP[exporter.py]
    end
    MW --> CV & LP & PP & SS & HS
    CV --> TOOLS
    TOOLS --> CTL
    LP & PP & MW --> CTL
    CTL --> CORE
    CV --> RD & CAM
    RD --> TES & TEX & ANI
    EXP --> RD
    SHP --> MX & GE
    DOC --> SHP
```

## Ciclo de desenho (paintGL)

```mermaid
flowchart TD
    A[Qt pede um frame] --> B[glViewport + limpar]
    B --> C[glOrtho com a janela do mundo<br/>calculada pela câmara]
    C --> D[Prancheta + grelha]
    D --> E[Para cada camada visível<br/>e cada objeto]
    E --> F{Animação a correr?}
    F -- sim --> G["M(t) = T(osc) · M · R(ωt) · S(p(t))"]
    F -- não --> H[M = T · R · Sh · S]
    G & H --> I[glPushMatrix + glMultMatrixf M]
    I --> J{Grupo?}
    J -- sim --> E
    J -- não --> K[Preenchimento: cor ou textura<br/>glDrawArrays GL_TRIANGLES]
    K --> L[glPopMatrix]
    L --> M[Contorno em coordenadas do mundo<br/>GL_TRIANGLE_STRIP]
    M --> E
    E -- fim --> N[Seleção, alças, pré-visualização]
    N --> O[Minimapa: 2.º glViewport]
    O --> P[HUD com QPainter]
```

## Interação (do clique à alteração)

```mermaid
sequenceDiagram
    participant U as Utilizador
    participant C as Canvas
    participant T as Ferramenta ativa
    participant K as Controller
    participant D as Documento
    U->>C: clique / arrasto (pixels)
    C->>C: câmara: ecrã → mundo
    C->>T: press / move / release (coordenadas do mundo)
    T->>D: hit test com M⁻¹, nova matriz M' (decomposição)
    T->>K: notify_modified / commit("Mover")
    K->>K: histórico: instantâneo JSON
    K-->>C: sinal objectsChanged → repintar
    K-->>U: painéis atualizados (Camadas, Propriedades)
```
