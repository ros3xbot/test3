import requests
from app.service.auth import AuthInstance
from app.client.balance import settlement_balance
from app.client.qris import show_qris_payment
from app.client.ewallet import show_multipayment
from app.client.engsel import get_package_details
from app.menus.util import clear_screen, pause
from app.menus.util_helper import print_panel, get_rupiah
from app.config.theme_config import get_theme
from app.menus.package import get_packages_by_family
from app.menus.family_grup import show_family_menu
from app.menus.bookmark import show_bookmark_menu
from app.type_dict import PaymentItem
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.text import Text
from rich.box import MINIMAL_DOUBLE_HEAD

console = Console()

def fetch_decoy_detail(api_key, tokens, url):
    response = requests.get(url, timeout=30)
    data = response.json()
    return get_package_details(
        api_key, tokens,
        data["family_code"],
        data["variant_code"],
        data["order"],
        data["is_enterprise"],
        data["migration_type"]
    )

def append_decoy_to_items(payment_items, decoy_detail):
    price = int(decoy_detail["package_option"]["price"])
    item = PaymentItem(
        item_code=decoy_detail["package_option"]["package_option_code"],
        product_type="",
        item_price=price,
        item_name=decoy_detail["package_option"]["name"],
        tax=0,
        token_confirmation=decoy_detail["token_confirmation"],
    )
    payment_items.append(item)
    return price  # ⬅️ Kembalikan harga langsung


def show_bundle_menu():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    theme = get_theme()

    cart_items = []
    display_cart = []
    total_price = 0

    while True:
        clear_screen()
        console.print(Panel(
            Align.center("🛒 Keranjang Paket Bundle", vertical="middle"),
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        if cart_items:
            table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
            table.add_column("No", justify="right", style=theme["text_key"], width=4)
            table.add_column("Nama Paket", style=theme["text_body"])
            table.add_column("Harga", style=theme["text_money"], justify="right")

            for i, item in enumerate(display_cart, start=1):
                table.add_row(str(i), item["name"], get_rupiah(item["price"]))

            console.print(Panel(table, border_style=theme["border_primary"], padding=(0, 1), expand=True))
            console.print(f"[{theme['text_body']}]Total Harga: Rp {get_rupiah(total_price)}[/]")
        else:
            print_panel("ℹ️ Info", "Keranjang masih kosong.")

        nav = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
        nav.add_column(justify="right", style=theme["text_key"], width=6)
        nav.add_column(style=theme["text_body"])
        nav.add_row("1", "Tambah dari Bookmark")
        nav.add_row("2", "Tambah dari Family Code Tersimpan")
        nav.add_row("3", "Tambah dari Family Code Manual")
        nav.add_row("4", f"[{theme['text_err']}]Hapus Item dari Keranjang[/]")
        if cart_items:
            nav.add_row("5", f"[{theme['text_warn']}]💳 Lanjutkan ke Pembayaran[/]")
        nav.add_row("00", f"[{theme['text_sub']}]Kembali ke menu utama[/]")

        console.print(Panel(nav, border_style=theme["border_info"], padding=(0, 1), expand=True))

        choice = console.input(f"[{theme['text_sub']}]Pilihan:[/{theme['text_sub']}] ").strip()

        def add_to_cart(detail, name):
            nonlocal total_price
            option = detail["package_option"]
            cart_items.append(PaymentItem(
                item_code=option["package_option_code"],
                product_type="", item_price=option["price"],
                item_name=option["name"], tax=0,
                token_confirmation=detail["token_confirmation"]
            ))
            display_cart.append({"name": name, "price": option["price"]})
            total_price += option["price"]
            print_panel("✅ Ditambahkan", f"Paket '{name}' berhasil masuk keranjang.")
            pause()

        if choice == "1":
            result = show_bookmark_menu(return_package_detail=True)
            if isinstance(result, tuple):
                detail, name = result
                if detail:
                    add_to_cart(detail, name)

        elif choice == "2":
            result = show_family_menu(return_package_detail=True)
            if result == "MAIN":
                break
            elif isinstance(result, tuple):
                detail, name = result
                if detail:
                    add_to_cart(detail, name)

        elif choice == "3":
            fc = console.input(f"[{theme['text_sub']}]Masukkan Family Code:[/{theme['text_sub']}] ").strip()
            result = get_packages_by_family(fc, return_package_detail=True)
            if result == "MAIN":
                break
            elif isinstance(result, tuple):
                detail, name = result
                if detail:
                    add_to_cart(detail, name)

        elif choice == "4" and cart_items:
            idx = console.input(f"[{theme['text_sub']}]Nomor item yang ingin dihapus:[/{theme['text_sub']}] ").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(cart_items):
                i = int(idx) - 1
                removed = display_cart.pop(i)
                cart_items.pop(i)
                total_price -= removed["price"]
                print_panel("🗑️ Dihapus", f"Item '{removed['name']}' telah dihapus.")
                pause()
            else:
                print_panel("⚠️ Error", "Nomor item tidak valid.")
                pause()

        elif choice == "5" and cart_items:
            clear_screen()
            info_text = Text()
            info_text.append("Detail Pembayaran:\n", style=theme["text_body"])
            for i, item in enumerate(display_cart, start=1):
                info_text.append(f"{i}. {item['name']} - Rp {get_rupiah(item['price'])}\n", style=theme["text_body"])
            info_text.append(f"\nTotal: Rp {get_rupiah(total_price)}", style=theme["text_money"])

            console.print(Panel(
                info_text,
                title=f"[{theme['text_title']}]Informasi Pembayaran[/]",
                border_style=theme["border_info"],
                padding=(1, 2),
                expand=True
            ))

            while True:
                method_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
                method_table.add_column(justify="right", style=theme["text_key"], width=6)
                method_table.add_column(style=theme["text_body"])
                method_table.add_row("1", "💰 Balance")
                method_table.add_row("2", "💳 E-Wallet")
                method_table.add_row("3", "📱 QRIS")
                method_table.add_row("4", "💰 Pulsa + Decoy XCP")
                method_table.add_row("5", "💰 Pulsa + Decoy XCP V2")
                method_table.add_row("6", "🔁 Pulsa N kali")
                method_table.add_row("7", "📱 QRIS + Decoy Edu")
                method_table.add_row("00", f"[{theme['text_sub']}]Kembali ke menu sebelumnya[/]")

                console.print(Panel(
                    method_table,
                    title=f"[{theme['text_title']}]💳 Pilih Metode Pembayaran[/]",
                    border_style=theme["border_primary"],
                    padding=(0, 1),
                    expand=True
                ))

                method = console.input(f"[{theme['text_sub']}]Pilih metode:[/{theme['text_sub']}] ").strip()

                if method == "00":
                    break

                confirm = console.input(f"[{theme['text_sub']}]Lanjutkan pembelian dengan metode ini? (y/n):[/{theme['text_sub']}] ").strip().lower()
                if confirm != "y":
                    print_panel("ℹ️ Info", "Pembayaran dibatalkan.")
                    pause()
                    continue

                if method == "1":
                    settlement_balance(api_key, tokens, cart_items, "BUY_PACKAGE", True)
                    console.input(f"[{theme['text_sub']}]✅ Pembayaran selesai. Tekan Enter...[/{theme['text_sub']}]")
                    break
                elif method == "2":
                    show_multipayment(api_key, tokens, cart_items, "BUY_PACKAGE", True)
                    console.input(f"[{theme['text_sub']}]✅ Pembayaran selesai. Tekan Enter...[/{theme['text_sub']}]")
                    break
                elif method == "3":
                    show_qris_payment(api_key, tokens, cart_items, "BUY_PACKAGE", True)
                    console.input(f"[{theme['text_sub']}]✅ Pembayaran selesai. Tekan Enter...[/{theme['text_sub']}]")
                    break

                elif method == "4" or method == "5":
                    try:
                        url = "https://me.mashu.lol/pg-decoy-xcp.json"
                        decoy_detail = fetch_decoy_detail(api_key, tokens, url)
                        decoy_price = append_decoy_to_items(cart_items, decoy_detail)
                        overwrite_amount = total_price + decoy_price
                        res = settlement_balance(api_key, tokens, cart_items, "BUY_PACKAGE", False, overwrite_amount, token_confirmation_idx=-1)
                
                        if res and res.get("status", "") != "SUCCESS":
                            msg = res.get("message", "")
                            if "Bizz-err.Amount.Total" in msg and "=" in msg:
                                valid_amount = int(msg.split("=")[1].strip())
                                print_panel("Info", f"Jumlah disesuaikan ke Rp {get_rupiah(valid_amount)}")
                                res = settlement_balance(api_key, tokens, cart_items, "BUY_PACKAGE", False, valid_amount, token_confirmation_idx=-1)
                
                        print_panel("✅ Info", "Pembelian berhasil." if res.get("status") == "SUCCESS" else "Gagal.")
                        pause(); break
                    except Exception as e:
                        print_panel("⚠️ Error", f"Gagal decoy XCP: {e}")
                        pause()
                
                elif method == "6":
                    try:
                        from app.client.repeat import purchase_n_times
                        use_decoy = console.input(f"[{theme['text_sub']}]Gunakan decoy? (y/n):[/{theme['text_sub']}] ").strip().lower() == "y"
                        n_times = int(console.input(f"[{theme['text_sub']}]Berapa kali pembelian:[/{theme['text_sub']}] ").strip())
                        delay = int(console.input(f"[{theme['text_sub']}]Delay antar pembelian (detik):[/{theme['text_sub']}] ").strip())
                        purchase_n_times(n_times, cart_items[0].item_code[:6], cart_items[0].item_code[6:9], cart_items[0].item_code[-1], use_decoy, delay, pause_on_success=False)
                        break
                    except Exception as e:
                        print_panel("⚠️ Error", f"Gagal pembelian N kali: {e}")
                        pause()
                
                elif method == "7":
                    try:
                        decoy_detail = fetch_decoy_detail(api_key, tokens, "https://me.mashu.lol/pg-decoy-edu.json")
                        decoy_price = append_decoy_to_items(cart_items, decoy_detail)
                
                        info_text = Text()
                        info_text.append(f"Harga Paket Utama: Rp {get_rupiah(total_price)}\n", style=theme["text_money"])
                        info_text.append(f"Harga Decoy Edu: Rp {get_rupiah(decoy_price)}\n", style=theme["text_money"])
                        info_text.append("Silahkan sesuaikan amount jika diperlukan (trial & error)", style=theme["text_body"])
                        console.print(Panel(info_text, title="📦 Info Pembayaran QRIS + Decoy", border_style=theme["border_warning"], expand=True))
                
                        show_qris_payment(api_key, tokens, cart_items, "SHARE_PACKAGE", True, token_confirmation_idx=1)
                        console.input(f"[{theme['text_sub']}]✅ QRIS selesai. Tekan Enter...[/{theme['text_sub']}]")
                        break
                    except Exception as e:
                        print_panel("⚠️ Error", f"Gagal decoy Edu: {e}")
                        pause()

                else:
                    print_panel("⚠️ Error", "Metode tidak valid.")
                    pause()

        elif choice == "00":
            break

        else:
            print_panel("⚠️ Error", "Pilihan tidak valid.")
            pause()
