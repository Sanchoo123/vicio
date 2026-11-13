# Vício — calendário de drops

Calendário dos próximos drops de streetwear (Supreme, Palace, Stüssy, Corteiz, Broken Planet, Nike, BAPE, Represent), com avisos no iPhone.

- `prototipo.html` — o visual (fase 1, com dados de exemplo)
- `robot/` — o robô que procura drops e manda avisos (fase 2)
- `data/` — o que o robô encontra e as tuas escolhas
- `.github/workflows/robo.yml` — corre o robô de 30 em 30 minutos no GitHub

## De onde vem a informação

| Marca | Fonte | O que dá |
|---|---|---|
| Represent | Catálogo público da loja | Peças novas, fotos, preços, restocks |
| BAPE | Catálogo público da loja (só 1× por hora, a loja limita pedidos) | Peças novas, fotos, preços, restocks |
| Nike / Jordan | Calendário oficial SNKRS Portugal (o de nike.com/pt/launch), de hora a hora | Hora exata em Portugal, preço em €, FCFS ou sorteio, fotos |
| Supreme, Palace | Ritmo habitual (Supreme quinta 16:00, Palace sexta 11:00, hora de Lisboa) + listas semanais da Hypebeast ("Everything Dropping at…") + Google Notícias | Drops previstos, confirmados quando sai a lista da semana |
| Stüssy, Corteiz, Broken Planet | Google Notícias (de hora a hora) + Hypebeast + Sole Retriever + o que acrescentares à mão | Notícias e drops anunciados |

As lojas da Supreme, Palace, Stüssy, Corteiz e Broken Planet bloqueiam robôs. O robô respeita isso: identifica-se sempre como `VicioDropCalendar`, faz um pedido de cada vez e, se uma fonte recusar, tenta só na ronda seguinte. Para essas marcas, o que vires no Instagram acrescenta-se em `data/manual.json`.

Os feeds de notícias só mostram os artigos mais recentes, por isso o calendário vai ficando mais completo com o tempo: o robô guarda tudo o que encontra.

## Pôr a funcionar

1. **No iPhone:** instala a app **ntfy** (App Store) → `+` → escreve o nome do teu tópico (um nome difícil de adivinhar, funciona como palavra-passe) → Subscribe.
2. **No GitHub:** cria um repositório **público** chamado `vicio` e envia esta pasta. Público porque assim o GitHub Actions e o GitHub Pages são grátis e sem limites. O nome do tópico nunca fica no código.
3. No repositório: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `NTFY_TOPIC`
   - Secret: o nome do tópico do passo 1
4. **Actions → Robô de drops → Run workflow.** Ao fim de um minuto recebes no iPhone "Robô do Vício ligado ✓".

A partir daí corre sozinho de 30 em 30 minutos.

## As tuas escolhas: `data/me.json`

- `avisos_por_marca` — `tudo`, `drops`, `meus` ou `nada` para cada marca.
  - `tudo`: notícias + drops + peças novas na loja
  - `drops`: só drops com data e peças novas na loja
  - `meus`: só os lembretes dos drops onde vais entrar
  - `nada`: sem avisos
- `vou_entrar` — drops onde vais entrar, com as peças por ordem de prioridade. O robô agenda um aviso 1 hora antes e outro 10 minutos antes ("faz login").
- `seguir_restock` — peças da Represent ou BAPE a vigiar; recebes aviso quando voltam a ter stock.

Na fase 3 o site passa a escrever este ficheiro sozinho quando carregas em "Vou entrar".

## Que avisos recebes

- Novo drop anunciado (com foto)
- Drop previsto confirmado, ou lista de peças revelada
- Mudança de data ou hora
- Peças novas a aparecer na loja (drop a acontecer)
- Restock de uma peça que segues
- Lembretes 1 h e 10 min antes dos drops onde vais entrar
- Resumo da semana ao domingo à noite

No máximo 8 avisos por ronda; o resto junta-se num só. Todos ficam também na lista **Avisos** da app.

## Notificações na própria app (em vez do ntfy)

A app Vício, instalada no ecrã principal do iPhone (iOS 16.4 ou mais recente), recebe as notificações diretamente.

1. Segredos no GitHub (uma vez): `VAPID_PRIVATE_KEY` (assina os envios) e `PUSH_BOX_KEY` (abre a subscrição do iPhone).
   As chaves públicas que fazem par com estes segredos estão no `index.html` (`VAPID_PUB`, `BOX_PUB`).
2. Na app: **Definições → Notificações na app → Ativar notificações** → permitir → **Enviar aviso de teste**.

A subscrição do iPhone fica em `data/me.json` (campo `push`), cifrada: o repositório é público e só o robô a consegue ler.
Enquanto houver um iPhone ligado, o robô deixa de usar o ntfy. Os lembretes de 1 h e 10 min são mandados à hora exata
pelo trabalho `lembretes` do workflow, que espera por eles; se a hora de um drop mudar ou deixares de entrar, o lembrete cai.

## Calendário do iPhone

O robô gera `data/drops.ics` (todos os drops) e `data/meus-drops.ics` (só os teus, com alertas). Na fase 3 ficam num link para subscrever em **Definições → Calendário → Contas → Adicionar conta → Outra → Calendário subscrito**.

## Correr no computador

```
python3 -m unittest tests.test_robot     # testes
python3 -m robot.run --dry-run           # uma ronda sem mandar avisos
```
