# Shadow PC Optimizer

O Shadow usa Python para coletar os dados do computador e HTML/CSS/JavaScript para desenhar a interface. A análise começa somente depois do clique em **Analisar**.

Na lista de processos, a pessoa pode pedir para encerrar um aplicativo específico. O Shadow pede confirmação, valida que o processo ainda é o mesmo e não força o encerramento se ele não responder. Salve o trabalho antes: encerrar um aplicativo pode causar perda de dados. Nenhum processo é encerrado automaticamente.

O painel também mostra o espaço livre nas unidades e oferece monitoramento ao vivo de CPU, RAM, processos e atividade do disco. No Windows, inclui uma prévia de temporários com mais de sete dias na pasta TEMP da conta, uma lista reversível dos itens da chave de inicialização da conta atual e a consulta/seleção de planos de energia. Limpeza, inicialização e plano de energia exigem confirmação. Arquivos temporários em uso são ignorados. O Shadow não promete aumento de FPS.

## Windows 10/11

### Para desenvolver

No PowerShell, abra a pasta do projeto e execute:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Se o Windows pedir o runtime do WebView, instale o Microsoft Edge WebView2 Runtime.

### Para gerar a versão para distribuir

Para compilar manualmente, use um computador Windows com Python 3. Abra o PowerShell na pasta do projeto e rode:

```powershell
.\build_windows.ps1
```

Será gerado um único arquivo em `dist\Shadow.exe`. O ambiente de compilação é recriado limpo e usa o Edge WebView2 do Windows, sem empacotar Qt ou GTK. O próprio script mostra o tamanho final em MB. O computador da pessoa não precisa de Python nem pip; precisa do Microsoft Edge WebView2 Runtime, que não é incluído para manter o download menor.

### Gerar pelo GitHub sem ter Windows

O fluxo `.github/workflows/build-windows.yml` compila o aplicativo em um runner Windows do GitHub Actions. Envie o projeto ao GitHub, abra a aba **Actions**, selecione **Build Shadow for Windows** e clique em **Run workflow**. Quando terminar, abra a execução e baixe o artefato **Shadow-Windows** na seção **Artifacts**. O arquivo baixado é um ZIP contendo `Shadow.exe`; o GitHub mantém o artefato por 14 dias.

O repositório precisa conter o código, `requirements.txt`, `build_windows.ps1`, esta pasta `.github` e a pasta `ui`. Não envie `.venv`, `dist` ou `build`; eles são excluídos pelo `.gitignore`.

## Linux de desenvolvimento

No VS Code, selecione o interpretador `/home/lcm_z/.venv/bin/python` para que o depurador use o ambiente em que o pywebview foi instalado.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

O arquivo `requirements.txt` escolhe o renderizador Qt do pywebview no Linux. Em sistemas Arch/CachyOS, instale primeiro o pacote de pip do sistema se `python -m pip` não estiver disponível.

Para usar o scanner no terminal:

```bash
python main.py --console
```
