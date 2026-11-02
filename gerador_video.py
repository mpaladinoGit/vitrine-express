import asyncio
import io
import os
import re
import subprocess
import textwrap
import time
import urllib.parse
import urllib.request
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageOps

DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_VIDEOS = os.path.join(DIRETORIO_BASE, "videos_gerados")
os.makedirs(PASTA_VIDEOS, exist_ok=True)

LINK_CURTO_LOJA = "is.gd/vitrineexpress"

# 5 Paletas Visuais Distintas para cada vídeo ter identidade própria no feed
TEMAS_VISUAIS = [
    {
        "nome": "neon_cyber",
        "bg_top": (12, 10, 38),
        "bg_bot": (32, 18, 77),
        "card_header": (26, 20, 64),
        "accent": (0, 229, 255),
        "tag_1": (219, 39, 119),
        "tag_2": (124, 58, 237),
        "cta_bg": (219, 39, 119),
        "cta_alt": (16, 185, 129),
        "price_box": (22, 18, 56),
        "price_color": (52, 211, 153),
    },
    {
        "nome": "oferta_fogo",
        "bg_top": (45, 10, 18),
        "bg_bot": (85, 20, 15),
        "card_header": (65, 15, 22),
        "accent": (251, 191, 36),
        "tag_1": (234, 88, 12),
        "tag_2": (220, 38, 38),
        "cta_bg": (234, 88, 12),
        "cta_alt": (22, 163, 74),
        "price_box": (55, 14, 20),
        "price_color": (253, 224, 71),
    },
    {
        "nome": "esmeralda_vip",
        "bg_top": (6, 36, 28),
        "bg_bot": (14, 68, 52),
        "card_header": (10, 50, 38),
        "accent": (250, 204, 21),
        "tag_1": (16, 185, 129),
        "tag_2": (217, 119, 6),
        "cta_bg": (217, 119, 6),
        "cta_alt": (5, 150, 105),
        "price_box": (8, 44, 34),
        "price_color": (110, 231, 183),
    },
    {
        "nome": "titanio_pro",
        "bg_top": (15, 23, 42),
        "bg_bot": (30, 58, 138),
        "card_header": (30, 41, 59),
        "accent": (56, 189, 248),
        "tag_1": (37, 99, 235),
        "tag_2": (245, 158, 11),
        "cta_bg": (245, 158, 11),
        "cta_alt": (22, 163, 74),
        "price_box": (23, 37, 84),
        "price_color": (74, 222, 128),
    },
    {
        "nome": "violeta_pop",
        "bg_top": (46, 16, 101),
        "bg_bot": (88, 28, 135),
        "card_header": (59, 7, 100),
        "accent": (244, 114, 182),
        "tag_1": (192, 38, 211),
        "tag_2": (234, 88, 12),
        "cta_bg": (234, 88, 12),
        "cta_alt": (22, 163, 74),
        "price_box": (49, 16, 82),
        "price_color": (253, 224, 71),
    },
]


def obter_fonte(tamanho, negrito=False):
    caminhos = (
        [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
        ]
        if negrito
        else [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
        ]
    )
    for c in caminhos:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, tamanho)
            except Exception:
                pass
    return ImageFont.load_default()


def formatar_moeda_br(valor):
    try:
        v = float(valor)
        inteiro = int(v)
        centavos = int(round((v - inteiro) * 100))
        inteiro_str = f"{inteiro:,}".replace(",", ".")
        return f"R$ {inteiro_str},{centavos:02d}"
    except Exception:
        return "R$ 0,00"


def formatar_preco_falado(valor):
    try:
        v = float(valor)
        reais = int(v)
        centavos = int(round((v - reais) * 100))
        if centavos > 0:
            return f"{reais} reais e {centavos} centavos"
        return f"{reais} reais"
    except Exception:
        return ""


def _indice_variacao(produto):
    try:
        cod_num = int(re.sub(r"\D+", "", str(produto.get("codigo") or "1")) or "1")
        return cod_num
    except Exception:
        return 1


def montar_roteiro_padrao(produto):
    titulo_completo = (produto.get("titulo") or "Produto em oferta").strip()
    palavras = titulo_completo.split()
    titulo_curto = " ".join(palavras[:8])
    plataforma_nome = produto.get("plataformaNome") or "Mercado Livre"
    preco_atual = float(produto.get("precoAtual") or 0)
    preco_antigo = float(produto.get("precoAntigo") or 0)

    fala_preco = ""
    if preco_antigo > preco_atual and preco_atual > 0:
        fala_preco = (
            f"Caiu de {formatar_preco_falado(preco_antigo)} "
            f"para apenas {formatar_preco_falado(preco_atual)}! "
        )
    elif preco_atual > 0:
        fala_preco = f"Está saindo por apenas {formatar_preco_falado(preco_atual)}! "

    templates = [
        (
            f"Você já viu quanto está custando esse {titulo_curto} hoje no {plataforma_nome}? "
            f"{fala_preco}"
            f"Aproveite enquanto dura o estoque: entre no link do nosso perfil "
            f"e clique no botão verde para abrir direto no {plataforma_nome}!"
        ),
        (
            f"Atenção para essa queda de preço no {plataforma_nome}! "
            f"{titulo_curto}. "
            f"{fala_preco}"
            f"Para garantir o seu com compra cem por cento segura, toque no link da nossa vitrine "
            f"e clique no botão verde da oferta!"
        ),
        (
            f"Esse é um dos campeões de vendas da semana no {plataforma_nome}! "
            f"{titulo_curto}. "
            f"{fala_preco}"
            f"Quer abrir direto no aplicativo oficial? Acesse a nossa vitrine no perfil "
            f"e toque no botão verde de compra!"
        ),
        (
            f"Se você estava procurando {titulo_curto} com excelente custo benefício, "
            f"olha essa oferta verificada no {plataforma_nome}! "
            f"{fala_preco}"
            f"Entre agora na nossa vitrine pelo link do perfil e clique no botão verde!"
        ),
        (
            f"Oferta relâmpago liberada hoje no {plataforma_nome}! "
            f"{titulo_curto}. "
            f"{fala_preco}"
            f"Para garantir o seu com total segurança, acesse a nossa vitrine "
            f"e clique no botão verde para abrir direto no {plataforma_nome}!"
        ),
    ]
    idx = _indice_variacao(produto) % len(templates)
    return templates[idx]


def montar_legenda_padrao(produto):
    titulo = (produto.get("titulo") or "Oferta Imperdível").strip()
    plataforma_nome = produto.get("plataformaNome") or "Mercado Livre"
    plataforma_tag = re.sub(r"\W+", "", plataforma_nome.lower())
    codigo = str(produto.get("codigo") or "01")
    preco_atual = formatar_moeda_br(produto.get("precoAtual") or 0)
    preco_antigo = float(produto.get("precoAntigo") or 0)
    atual_num = float(produto.get("precoAtual") or 0)

    linha_preco = f"💰 Por apenas {preco_atual}!"
    if preco_antigo > atual_num:
        linha_preco = f"💰 De {formatar_moeda_br(preco_antigo)} por apenas {preco_atual}!"

    ganchos_legenda = [
        f"🔥 Queda de preço verificada hoje no {plataforma_nome}!",
        f"⚡ Campeão de vendas em promoção no {plataforma_nome}!",
        f"🎯 Achadinho útil com super desconto no {plataforma_nome}!",
        f"🚨 Oferta relâmpago selecionada no {plataforma_nome}!",
    ]
    gancho = ganchos_legenda[_indice_variacao(produto) % len(ganchos_legenda)]

    return (
        f"{gancho}\n\n"
        f"📦 {titulo} (Item #{codigo})\n"
        f"{linha_preco}\n\n"
        f"👇 COMO COMPRAR NO SITE OFICIAL:\n"
        f"1️⃣ Toque no nosso perfil e clique no link da Vitrine ({LINK_CURTO_LOJA})\n"
        f"2️⃣ Clique no botão verde da oferta para abrir direto no {plataforma_nome}!\n\n"
        f"🔒 Compra 100% segura direto no app oficial ({plataforma_nome}).\n\n"
        f"#achadinhos #ofertas #{plataforma_tag} #promocao #desconto #vitrineexpress #dicasdecompras"
    )


def _baixar_img_url(url_img):
    if not url_img or not str(url_img).startswith("http"):
        return None
    try:
        req = urllib.request.Request(
            url_img,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=7) as resp:
            dados = resp.read(5_000_000)
            return Image.open(io.BytesIO(dados)).convert("RGB")
    except Exception:
        return None


def obter_galeria_imagens_produto(produto):
    """
    Busca a foto oficial em Full HD (-O.webp no Mercado Livre) + fotos extras de ângulos/variações
    no catálogo do Buscapé para que o vídeo mostre várias imagens dinâmicas em vez de 1 foto estática.
    """
    imagens = []
    url_principal = str(produto.get("imagem") or "").strip()

    # Tenta versão Full HD do Mercado Livre (-O.webp)
    if "mlstatic.com" in url_principal and url_principal.endswith("-P.webp"):
        url_hd = url_principal[:-7] + "-O.webp"
        img_hd = _baixar_img_url(url_hd)
        if img_hd:
            imagens.append(img_hd)

    if not imagens and url_principal:
        img_p = _baixar_img_url(url_principal)
        if img_p:
            imagens.append(img_p)

    # Busca até 3 fotos complementares no catálogo do Buscapé
    titulo = (produto.get("titulo") or "").strip()
    palavras = " ".join(titulo.split()[:6]).strip()
    if palavras:
        try:
            q = urllib.parse.urlencode({"q": palavras})
            req = urllib.request.Request(
                f"https://www.buscape.com.br/search?{q}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                html_b = resp.read(500_000).decode("utf-8", errors="ignore")
                urls_extras = list(
                    dict.fromkeys(re.findall(r"https://i\.zst\.com\.br/thumbs/[A-Za-z0-9/_.-]+\.jpg", html_b))
                )
                for u_ex in urls_extras[:3]:
                    im = _baixar_img_url(u_ex)
                    if im:
                        imagens.append(im)
        except Exception:
            pass

    if not imagens:
        # Imagem neutra caso não haja internet
        placeholder = Image.new("RGB", (600, 600), (255, 255, 255))
        imagens.append(placeholder)

    return imagens


def desenhar_retangulo_arredondado(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def centralizar_texto(draw, W, y, texto, fonte, cor):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), texto, font=fonte, fill=cor)


def criar_slide_cena(produto, galeria_imgs, numero_cena, total_cenas, tema):
    """
    Gera 5 cenas dinâmicas 720x1280 (9:16), variando:
    - Tema de cores por produto
    - Ângulo/foto ou composição dupla (vitrine interativa)
    - Legenda estilo TikTok/Reels sincronizada com o momento do vídeo
    - Barra de progresso visual
    """
    W, H = 720, 1280
    base = Image.new("RGB", (W, H), tema["bg_top"])
    draw = ImageDraw.Draw(base)

    r1, g1, b1 = tema["bg_top"]
    r2, g2, b2 = tema["bg_bot"]
    for y in range(H):
        fator = y / H
        r = int(r1 + fator * (r2 - r1))
        g = int(g1 + fator * (g2 - g1))
        b = int(b1 + fator * (b2 - b1))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    f_logo = obter_fonte(31, negrito=True)
    f_sub = obter_fonte(20, negrito=True)
    f_tag = obter_fonte(25, negrito=True)
    f_titulo = obter_fonte(26, negrito=True)
    f_legenda_dinamica = obter_fonte(25, negrito=True)
    f_preco_ant = obter_fonte(25, negrito=False)
    f_preco_atu = obter_fonte(54, negrito=True)
    f_link_gigante = obter_fonte(36, negrito=True)

    plataforma_nome = (produto.get("plataformaNome") or "Mercado Livre").upper()
    codigo = str(produto.get("codigo") or "01")
    preco_atual = float(produto.get("precoAtual") or 0)
    preco_antigo = float(produto.get("precoAntigo") or 0)
    desconto = 0
    if preco_antigo > preco_atual and preco_antigo > 0:
        desconto = int(round(((preco_antigo - preco_atual) / preco_antigo) * 100))

    # Topo da Marca com a cor do Tema
    desenhar_retangulo_arredondado(
        draw, (36, 30, W - 36, 114), 18, fill=tema["card_header"], outline=tema["accent"], width=3
    )
    centralizar_texto(draw, W, 40, "VITRINE EXPRESS", f_logo, (255, 255, 255))
    centralizar_texto(draw, W, 79, f"CURADORIA OFICIAL • {plataforma_nome}", f_sub, tema["accent"])

    # Gancho superior muda a cada cena
    ganchos_cena = {
        1: ("OLHA ESSE ACHADINHO EM OFERTA!", tema["tag_1"]),
        2: ("QUALIDADE NOTA 4.9 ESTRELAS!", tema["tag_2"]),
        3: (f"DESCONTO ESPECIAL DE {desconto or 20}% HOJE!", (22, 163, 74)),
        4: ("ESTOQUE PROMOCIONAL LIMITADO!", tema["tag_1"]),
        5: ("GARANTA O SEU NO SITE OFICIAL:", (22, 163, 74)),
    }
    texto_topo, cor_topo = ganchos_cena.get(numero_cena, ganchos_cena[1])
    desenhar_retangulo_arredondado(draw, (46, 128, W - 46, 184), 14, fill=cor_topo)
    centralizar_texto(draw, W, 141, texto_topo, f_tag, (255, 255, 255))

    # Quadro da Foto do Produto (Cenas 1 a 5 variam entre foto principal, ângulos extras, zoom e visão dupla!)
    card_top = 198
    card_bottom = 668
    desenhar_retangulo_arredondado(
        draw, (42, card_top, W - 42, card_bottom), 24, fill=(255, 255, 255), outline=tema["accent"], width=3
    )

    img_principal = galeria_imgs[0]
    img_secundaria = galeria_imgs[min(1, len(galeria_imgs) - 1)]
    img_terciaria = galeria_imgs[min(2, len(galeria_imgs) - 1)]

    if numero_cena == 1:
        # Cena 1: Foto Principal limpa em destaque
        img_c = img_principal.copy()
        img_c.thumbnail((540, 410), Image.Resampling.LANCZOS)
        px = (W - img_c.width) // 2
        py = card_top + ((card_bottom - card_top) - img_c.height) // 2
        base.paste(img_c, (px, py))

    elif numero_cena == 2:
        # Cena 2: Ângulo 2 (ou Super Zoom no detalhe central da foto principal)
        if len(galeria_imgs) > 1:
            img_c = img_secundaria.copy()
            img_c.thumbnail((560, 420), Image.Resampling.LANCZOS)
        else:
            w_o, h_o = img_principal.size
            crop_box = (int(w_o * 0.1), int(h_o * 0.1), int(w_o * 0.9), int(h_o * 0.9))
            img_c = img_principal.crop(crop_box)
            img_c.thumbnail((560, 420), Image.Resampling.LANCZOS)
        px = (W - img_c.width) // 2
        py = card_top + ((card_bottom - card_top) - img_c.height) // 2
        base.paste(img_c, (px, py))

    elif numero_cena == 3:
        # Cena 3: Visão Dupla Lado a Lado (Vitrine Comparativa!)
        img_esq = img_principal.copy()
        img_esq.thumbnail((285, 360), Image.Resampling.LANCZOS)
        img_dir = (img_terciaria if len(galeria_imgs) > 2 else img_secundaria).copy()
        img_dir.thumbnail((285, 360), Image.Resampling.LANCZOS)

        y_esq = card_top + ((card_bottom - card_top) - img_esq.height) // 2
        y_dir = card_top + ((card_bottom - card_top) - img_dir.height) // 2
        base.paste(img_esq, (68, y_esq))
        base.paste(img_dir, (W - 68 - img_dir.width, y_dir))
        draw.line([(W // 2, card_top + 30), (W // 2, card_bottom - 30)], fill=(226, 232, 240), width=3)

    elif numero_cena == 4:
        # Cena 4: Foto com Super Zoom Dinâmico + Selo de Aprovação
        img_c = (img_terciaria if len(galeria_imgs) > 2 else img_principal).copy()
        img_c.thumbnail((580, 430), Image.Resampling.LANCZOS)
        px = (W - img_c.width) // 2
        py = card_top + ((card_bottom - card_top) - img_c.height) // 2
        base.paste(img_c, (px, py))

    else:
        # Cena 5: Fechamento de Compra com Foto Principal em Destaque Máximo
        img_c = img_principal.copy()
        img_c.thumbnail((550, 415), Image.Resampling.LANCZOS)
        px = (W - img_c.width) // 2
        py = card_top + ((card_bottom - card_top) - img_c.height) // 2
        base.paste(img_c, (px, py))

    # Etiqueta ITEM #XX
    desenhar_retangulo_arredondado(draw, (60, card_top + 14, 225, card_top + 66), 12, fill=(15, 23, 42))
    draw.text((78, card_top + 23), f"ITEM #{codigo}", font=f_tag, fill=tema["accent"])

    # Etiqueta de Desconto ou Nota
    if numero_cena in (2, 4):
        desenhar_retangulo_arredondado(draw, (W - 265, card_top + 14, W - 60, card_top + 66), 12, fill=(245, 158, 11))
        draw.text((W - 246, card_top + 23), "NOTA 4.9 / 5.0", font=f_tag, fill=(15, 23, 42))
    elif desconto > 0:
        desenhar_retangulo_arredondado(draw, (W - 230, card_top + 14, W - 60, card_top + 66), 12, fill=(22, 163, 74))
        draw.text((W - 210, card_top + 23), f"-{desconto}% OFF", font=f_tag, fill=(255, 255, 255))

    # Faixa de Legenda Dinâmica (Estilo CapCut / TikTok) mudando a cada cena!
    legendas_curtas = {
        1: "Oferta selecionada com menor preço!",
        2: "Produto bem avaliado e campeão de pedidos",
        3: f"Economize garantindo hoje por {formatar_moeda_br(preco_atual)}",
        4: "Link verificado no perfil da nossa loja",
        5: "Toque no botão verde e compre no app oficial!",
    }
    frase_cena = legendas_curtas.get(numero_cena, legendas_curtas[1])
    desenhar_retangulo_arredondado(
        draw, (52, card_bottom - 58, W - 52, card_bottom - 10), 12, fill=(15, 23, 42)
    )
    centralizar_texto(draw, W, card_bottom - 49, frase_cena, f_legenda_dinamica, (254, 240, 138))

    # Título do Produto
    titulo = (produto.get("titulo") or "Produto em Oferta").strip()
    linhas_titulo = textwrap.wrap(titulo, width=36)[:2]
    y_t = 684
    for linha in linhas_titulo:
        centralizar_texto(draw, W, y_t, linha, f_titulo, (255, 255, 255))
        y_t += 34

    # Bloco de Preço
    desenhar_retangulo_arredondado(
        draw, (42, 764, W - 42, 950), 20, fill=tema["price_box"], outline=tema["price_color"], width=2
    )
    if preco_antigo > preco_atual:
        txt_ant = f"De {formatar_moeda_br(preco_antigo)}"
        bbox_a = draw.textbbox((0, 0), txt_ant, font=f_preco_ant)
        tw_a = bbox_a[2] - bbox_a[0]
        x_a = (W - tw_a) // 2
        draw.text((x_a, 776), txt_ant, font=f_preco_ant, fill=(203, 213, 225))
        draw.line([(x_a, 793), (x_a + tw_a, 793)], fill=(239, 68, 68), width=3)

    txt_atu = f"Por {formatar_moeda_br(preco_atual)}"
    centralizar_texto(draw, W, 810, txt_atu, f_preco_atu, tema["price_color"])
    condicao_txt = (
        f"Frete Grátis • Compra Segura no {produto.get('plataformaNome', 'Site Oficial')}"
        if preco_atual >= 79
        else f"no Pix • Compra 100% Segura no {produto.get('plataformaNome', 'Site Oficial')}"
    )
    centralizar_texto(draw, W, 898, condicao_txt, f_sub, (241, 245, 249))

    # Bloco Inferior de Chamada para Ação
    cor_box_cta = tema["cta_alt"] if numero_cena in (3, 5) else tema["cta_bg"]
    desenhar_retangulo_arredondado(
        draw, (36, 972, W - 36, 1225), 22, fill=cor_box_cta, outline=(254, 240, 138), width=4
    )
    centralizar_texto(draw, W, 988, "COMO COMPRAR? ACESSE O LINK DO PERFIL:", f_sub, (255, 255, 255))

    desenhar_retangulo_arredondado(draw, (64, 1024, W - 64, 1098), 14, fill=(15, 23, 42))
    centralizar_texto(draw, W, 1034, LINK_CURTO_LOJA, f_link_gigante, (251, 191, 36))

    centralizar_texto(draw, W, 1116, "CLIQUE NO BOTÃO VERDE DE COMPRA", f_tag, (255, 255, 255))
    centralizar_texto(draw, W, 1160, f"E ABRA DIRETO NO {plataforma_nome}!", f_sub, (254, 240, 138))

    # Barra de Progresso no rodapé do vídeo
    prog_w = int(((W - 72) * numero_cena) / max(1, total_cenas))
    desenhar_retangulo_arredondado(draw, (36, 1242, W - 36, 1256), 6, fill=(30, 41, 59))
    desenhar_retangulo_arredondado(draw, (36, 1242, 36 + prog_w, 1256), 6, fill=tema["accent"])

    return base


async def _salvar_audio_tts(texto, voz, caminho_mp3):
    comunicador = edge_tts.Communicate(texto, voz, rate="+8%")
    await comunicador.save(caminho_mp3)


def obter_duracao_audio(caminho_mp3):
    try:
        proc = subprocess.run(
            ["ffmpeg", "-i", caminho_mp3],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
        if m:
            horas = int(m.group(1))
            minutos = int(m.group(2))
            segundos = float(m.group(3))
            return horas * 3600 + minutos * 60 + segundos
    except Exception:
        pass
    return 12.0


def gerar_video_produto(produto, roteiro_custom="", voz=""):
    codigo = re.sub(r"\W+", "", str(produto.get("codigo") or "01"))
    timestamp = int(time.time())
    nome_base = f"vitrine_express_cod_{codigo}_{timestamp}"
    caminho_mp3 = os.path.join(PASTA_VIDEOS, f"{nome_base}.mp3")
    caminho_mp4 = os.path.join(PASTA_VIDEOS, f"{nome_base}.mp4")

    # Se não escolheu voz fixa, alterna entre Francisca e Antônio para variar os vídeos do perfil
    if not voz:
        voz = "pt-BR-FranciscaNeural" if (_indice_variacao(produto) % 2 == 0) else "pt-BR-AntonioNeural"

    roteiro = (roteiro_custom or "").strip() or montar_roteiro_padrao(produto)
    legenda = montar_legenda_padrao(produto)

    asyncio.run(_salvar_audio_tts(roteiro, voz, caminho_mp3))
    duracao = max(8.0, obter_duracao_audio(caminho_mp3))

    galeria_imgs = obter_galeria_imagens_produto(produto)
    tema = TEMAS_VISUAIS[_indice_variacao(produto) % len(TEMAS_VISUAIS)]

    total_cenas = 5
    caminhos_slides = []
    for c in range(1, total_cenas + 1):
        slide = criar_slide_cena(produto, galeria_imgs, c, total_cenas, tema)
        caminho_s = os.path.join(PASTA_VIDEOS, f"{nome_base}_s{c}.png")
        slide.save(caminho_s, "PNG")
        caminhos_slides.append(caminho_s)

    dur_cena = round(duracao / float(total_cenas), 2)
    caminho_lista = os.path.join(PASTA_VIDEOS, f"{nome_base}_concat.txt")
    with open(caminho_lista, "w", encoding="utf-8") as f:
        for cs in caminhos_slides:
            cs_ff = cs.replace("\\", "/")
            f.write(f"file '{cs_ff}'\n")
            f.write(f"duration {dur_cena}\n")
        ultimo_ff = caminhos_slides[-1].replace("\\", "/")
        f.write(f"file '{ultimo_ff}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        caminho_lista,
        "-i",
        caminho_mp3,
        "-vf",
        "fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-shortest",
        caminho_mp4,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True)

    for arq_temp in [*caminhos_slides, caminho_lista, caminho_mp3]:
        try:
            if os.path.exists(arq_temp):
                os.remove(arq_temp)
        except Exception:
            pass

    return {
        "sucesso": True,
        "arquivo": f"videos_gerados/{nome_base}.mp4",
        "caminhoCompleto": caminho_mp4,
        "roteiro": roteiro,
        "legenda": legenda,
        "duracao": round(duracao, 1),
    }
