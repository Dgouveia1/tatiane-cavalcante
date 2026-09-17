# Cartão de visita virtual — Tatiane Cavalcanti

Página única (HTML + CSS + JS vanilla, sem build) que substitui o Linktree: links das redes,
WhatsApp, prévia dos serviços e contato. Tema escuro + dourado.

```
index.html      página
css/style.css   estilos (tokens em :root)
js/main.js      animações e conveniências (a página funciona sem JS)
assets/         foto recortada (webp/png), QR, og.jpg, apple-touch-icon
.htaccess       cache/compressão/headers (HTTPS comentado — ver abaixo)
scripts/        geração dos assets e do zip (NÃO vai para o servidor)
```

## Editar links e textos

Tudo está em `index.html`. Cada botão é um `<a class="btn">` com `href`, título e subtítulo.
Os dois botões de WhatsApp usam mensagens pré-preenchidas diferentes (`?text=`), para a Tatiane
saber de onde veio o contato:

- **Fale comigo** → "Olá, Tatiane! Vim pelo seu cartão virtual e quero conversar sobre uma parceria."
- **Cursos** → "Olá, Tatiane! Tenho interesse nos seus cursos. Pode me passar mais informações?"

Para mudar a mensagem, codifique o texto (ex.: `encodeURIComponent` no console do navegador) e troque o `text=`.

## Pendências até o go-live final (procure `TODO:` nos arquivos)

| O quê | Onde |
|---|---|
| Domínio final (`https://DOMINIO/`) | `index.html` (canonical, og:url, og:image, JSON-LD, linha do site no contato), `.htaccess` |
| E-mail de contato | `index.html` — bloco `TODO:EMAIL` comentado no card de contato |
| QR code com o domínio final | `python scripts/make_qr.py https://dominio/` |
| HTTPS forçado | `.htaccess` — descomentar o bloco **só depois** que o AutoSSL do cPanel emitir o certificado |

## Regenerar assets

```bash
pip install opencv-python-headless pillow segno
python scripts/cutout.py --preview      # foto: scripts/_raw/tati.jpg -> assets/tati.webp + tati.png
python scripts/make_qr.py <url>          # assets/qr.svg
python scripts/make_icons.py             # assets/apple-touch-icon.png
python scripts/fetch_fonts.py            # assets/fonts/*.woff2 + css/fonts.css (fontes self-hosted)
```

### Recorte da foto

`cutout.py` tenta, nesta ordem: **rembg** (precisa do onnxruntime nativo, que no Windows exige o
[Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)) → **isnet em WASM via Node**
(`npm i onnxruntime-web` dentro de `scripts/` e o modelo em `scripts/_raw/isnet-general-use.onnx`,
baixado de https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx) →
**GrabCut** (OpenCV, sem modelo; bordas piores). O resultado do modelo é refinado com GrabCut para
remover o halo da parede sombreada.

### Imagem de compartilhamento (og.jpg)

`scripts/og.html` é um layout fixo 1200×630 que reutiliza o CSS. Screenshot com Playwright:

```bash
npx playwright screenshot --viewport-size=1200,630 --wait-for-timeout=1500 scripts/og.html assets/og.jpg
```

(sem Playwright: abra `scripts/og.html` no Chrome → DevTools → device toolbar 1200×630 → "Capture screenshot").

## Testar localmente

```bash
python -m http.server 8080
# http://localhost:8080
```

## Publicar no cPanel (HostGator)

1. `powershell -ExecutionPolicy Bypass -File scripts\build-zip.ps1` → gera `dist/tatiane-cavalcante.zip`
   (só `index.html`, `css/`, `js/`, `assets/`, `.htaccess`). **Gere o zip sempre depois da última edição** — o script imprime a data/hora.
2. cPanel → **Gerenciador de Arquivos** → `public_html` → ative *Configurações → Mostrar arquivos ocultos*.
3. Apague o `index.html`/`default.html` de exemplo da HostGator, se existir.
4. **Carregar** o zip → clique com o botão direito → **Extract** → apague o zip.
5. Confira permissões: arquivos 644, pastas 755.
6. A URL temporária (`…meusitehostgator.com.br`) só responde depois da propagação de DNS (até 72 h).

Atualizações: repita os passos 1 e 4 (extrair sobrescreve os arquivos).

Segurança: a senha do cPanel **nunca** entra neste repositório. Recomende à cliente trocá-la após o go-live.
