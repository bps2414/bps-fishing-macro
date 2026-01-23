# Checklist de Distribuição - BPS Fishing Macro V3.1

Antes de distribuir a nova versão, execute os seguintes testes manuais para garantir estabilidade e funcionalidade.

## 1. Verificações Iniciais e Interface (GUI)
- [ ] **Abertura do App**: O programa abre sem erros? O tema (escuro/azul) carrega corretamente?
- [ ] **Permissões**: O programa solicita/tem permissão de administrador (necessário para cliques simulados)?
- [ ] **Carregamento de Configurações**: As configurações anteriores (posições, hotkeys) são carregadas corretamente ao iniciar?
- [ ] **Tooltips**: Passe o mouse sobre as opções. As dicas (tooltips) aparecem corretamente?
- [ ] **Botões de Controle**:
    - [ ] Botão "Start" inicia a macro?
    - [ ] Botão "Stop" (ou Hotkey F3) para a macro imediatamente?
    - [ ] Checkboxes salvam o estado ao fechar e abrir de novo?

## 2. Configuração de Coordenadas (Setup)
- [ ] **Área de Pesca (F2)**: A seleção da área de pesca desenha o retângulo verde corretamente na tela?
- [ ] **Pontos de Clique**:
    - [ ] "Water Point" (ponto da água) é selecionável e salva?
    - [ ] Pontos do menu de Craft (Botão Craft, Plus, Ícones de Isca) são selecionáveis?
- [ ] **Identificação de Cores**:
    - [ ] O seletor de cor da fruta (Fruit Point) captura a cor correta sob o mouse?

## 3. Lógica de Pesca (Core)
- [ ] **Lançamento (Cast)**: A barra de força é carregada pelo tempo configurado (ex: 1.0s) e solta?
- [ ] **Detecção da Isca**: O "shake" (tremida) da boia é detectado corretamente?
- [ ] **Minigame**:
    - [ ] A barra verde é detectada e seguida corretamente pela barra branca (PID controller)?
    - [ ] O macro recupera se a barra se mover rápido demais?
- [ ] **Reload/Recast**: Se nenhum peixe for fisgado no tempo limite (Recast Timeout), ele puxa e joga de novo?

## 4. Funcionalidades Avançadas & V3.1 Específicas
- [ ] **Auto Craft**:
    - [ ] Ative o Auto Craft. Ele abre o menu após N peixes (conforme configurado)?
    - [ ] Ele clica nos botões corretos (Craft -> Selecionar Isca -> Craftar)?
    - [ ] Ele fecha o menu e volta a pescar?
- [ ] **Auto Store Fruit**:
    - [ ] Simule uma fruta (ou use uma real se possível). O macro detecta a cor da fruta?
    - [ ] A câmera gira e reseta (ou não) conforme a configuração "Disable Normal Camera"?
    - [ ] O macro navega até o inventário/loja para guardar?
- [ ] **Disable Normal Camera**:
    - [ ] Com a opção ativada: A câmera **NÃO** deve girar/zoom em modo normal (apenas pescando).
    - [ ] Com a opção desativada: A câmera deve fazer o reset padrão se configurado.
- [ ] **Estatísticas (Stats & DB)**:
    - [ ] O contador de Peixes e Frutas aumenta na aba Stats?
    - [ ] O cálculo "Rate/h" parece coerente após alguns minutos?
    - [ ] (Avançado) Verifique se o arquivo `fishing_stats.db` está sendo atualizado (tamanho do arquivo muda).

## 5. Performance e Estabilidade
- [ ] **Uso de CPU/Memória**: O macro não está consumindo 100% de CPU inutilmente?
- [ ] **Logs**: Verifique o arquivo `fishing_macro.log`. Há erros "ERROR" ou "CRITICAL" aparecendo?
- [ ] **Fim de Sessão**: Ao fechar o programa, ele encerra todos os threads e processos (sem ficar "preso" no gerenciador de tarefas)?

## 6. Distribuição (Build)
- [ ] **Compilação**: O comando de build (Nuitka/PyInstaller) roda sem erros?
- [ ] **Teste do Executável**: O `.exe` gerado roda em um PC limpo (ou numa pasta separada) sem pedir arquivos de dev (como .py)?
- [ ] **Licença**: O arquivo LICENSE está incluído na pasta de distribuição?
