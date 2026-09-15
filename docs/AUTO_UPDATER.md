# Auto-Updater com Inno Setup e Launcher Integrado

Este documento detalha a arquitetura e funcionamento do sistema de atualizacao automatica do **Crinometro**, projetado para releases no GitHub empacotadas com o **Inno Setup Compiler**.

---

## 1. Visao Geral do Fluxo

1. O Launcher inicializa duas threads paralelas:
   - Carregamento do core do programa (DSP, bibliotecas pesadas e janela principal).
   - Verificacao de novas releases na API do GitHub.
2. Caso exista nova versao:
   - O Launcher interrompe a abertura automatica do app.
   - Apresenta as opcoes **Atualizar Agora** e **Lembrar Mais Tarde**.
   - Se o usuario escolher **Lembrar Mais Tarde**, o aplicativo abre normalmente.
   - Se o usuario escolher **Atualizar Agora**:
     - O download do instalador e iniciado com barra de progresso em tempo real.
     - As mensagens de status se sucedem: *Baixando atualizacao*, *Verificando arquivos*, *Instalando arquivos* e *Reiniciando o programa*.
     - O processo desacoplado executa o instalador do Inno Setup em modo silencioso e reinicia o app na nova versao.

---

## 2. Componentes

- **core/updater.py**: Gerencia a comunicacao assincrona com o GitHub, comparador de versao SemVer, download com medicao de progresso em blocos e script batch de substituição silenciosa com Inno Setup.
- **crinometro__laucher.py**: Interface grafica interativa com botoes customizados, barra de progresso nativa desenhada no canvas QPainter e transicoes de estado protegidas.
- **extras/build/build_installer.py**: Automacao de compilacao que gera a pasta onedir no PyInstaller e invoca o ISCC.exe do Inno Setup para gerar o instalador em extras/dist/Download Versions/.
