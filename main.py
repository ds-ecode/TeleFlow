import os
import time
import asyncio
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# Import private credentials safely
try:
    from config import API_ID, API_HASH, GROUP_TARGET, STRING_SESSION
except ImportError:
    raise RuntimeError("config.py file is missing! Please create it with your API credentials.")

WORK_DIR = os.getcwd()
PROCESSED_FILE = os.path.join(WORK_DIR, 'processed_ids.txt')
DOWNLOAD_DIR = os.path.join(WORK_DIR, 'downloads/')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def load_processed_ids():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE, 'r') as f:
        return set(int(line.strip()) for line in f if line.strip().isdigit())

def save_processed_id(msg_id):
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{msg_id}\n")

class CleanTracker:
    def callback(self, current, total):
        if total > 0:
            percent = (current / total) * 100
            curr_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            print(f"\r    -> Progress: {curr_mb:.2f}MB / {total_mb:.2f}MB ({percent:.1f}%)    ", end="", flush=True)

tracker = CleanTracker()
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

async def main():
    print("Connecting to Telegram securely via StringSession...")
    processed_ids = load_processed_ids()
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    print(f"\nScanning group files in target chat: {GROUP_TARGET}...")
    all_media_messages = []
    pending_messages = []
    
    async for message in client.iter_messages(GROUP_TARGET, reverse=True):
        if message.media:
            file_obj = getattr(message, 'file', None)
            if not file_obj:
                continue 
            
            all_media_messages.append(message)
            raw_name = getattr(file_obj, 'name', None) or f"media_{message.id}{getattr(file_obj, 'ext', '')}"
            safe_filename = os.path.basename(raw_name)
            
            base_name, file_ext = os.path.splitext(safe_filename)
            clean_mp4_filename = f"{base_name}.mp4"
            local_mp4_path = os.path.join(DOWNLOAD_DIR, clean_mp4_filename)

            is_already_mp4 = file_ext.lower() == '.mp4'
            exists_locally = os.path.exists(local_mp4_path)
            in_processed_log = message.id in processed_ids

            if not in_processed_log and not is_already_mp4 and not exists_locally:
                pending_messages.append(message)

    print("\n" + "="*50)
    print(f" GROUP FILE INVENTORY SUMMARY")
    print("="*50)
    print(f" Total media files found in group: {len(all_media_messages)}")
    print(f" Previously logged as completed:   {len(processed_ids)}")
    print(f" Files remaining to process:       {len(pending_messages)}")
    print("="*50 + "\n")

    if not pending_messages:
        print("No files need processing. Exiting safely.")
        return

    session_processed_count = 0

    for idx, message in enumerate(pending_messages, 1):
        file_obj = getattr(message, 'file', None)
        raw_name = getattr(file_obj, 'name', None) or f"media_{message.id}"
        safe_filename = os.path.basename(raw_name)
        expected_size = getattr(file_obj, 'size', 0)
        
        base_name, _ = os.path.splitext(safe_filename)
        clean_mp4_filename = f"{base_name}.mp4"
        local_mp4_path = os.path.join(DOWNLOAD_DIR, clean_mp4_filename)

        print(f"\n[{idx}/{len(pending_messages)}] File: '{safe_filename}' (Msg ID: {message.id})")

        try:
            file_is_complete = False
            if os.path.exists(local_mp4_path):
                local_size = os.path.getsize(local_mp4_path)
                if expected_size > 0 and abs(local_size - expected_size) < 1024:
                    file_is_complete = True
                    print("    -> Found valid complete local file. Skipping download.")
                else:
                    print("    -> Cleaning up corrupted/partial local file...")
                    os.remove(local_mp4_path)

            # --- DOWNLOAD STAGE ---
            if not file_is_complete:
                print("    -> Status: Downloading...")
                dl_start = time.time()
                downloaded_path = None
                
                for attempt in range(1, 4):
                    try:
                        downloaded_path = await asyncio.wait_for(
                            message.download_media(file=DOWNLOAD_DIR, progress_callback=tracker.callback),
                            timeout=1500
                        )
                        break
                    except asyncio.TimeoutError:
                        print(f"\n    [!] Download timed out on attempt {attempt}/3. Retrying...")
                        await asyncio.sleep(5)
                    except Exception as net_err:
                        err_msg = str(net_err).strip() or "Connection reset / Network drop"
                        print(f"\n    [!] Network error on download attempt {attempt}/3: {err_msg}. Retrying...")
                        await asyncio.sleep(5)
                
                print()
                if not downloaded_path:
                    print("    -> Download failed after 3 attempts. Skipping item safely...")
                    continue

                if downloaded_path != local_mp4_path:
                    if os.path.exists(local_mp4_path):
                        os.remove(local_mp4_path)
                    os.rename(downloaded_path, local_mp4_path)
                
                dl_time = time.time() - dl_start
                print(f"    -> Download complete! Time taken: {dl_time:.1f} seconds.")

            print(f"    -> Output ready: {clean_mp4_filename}")

            # --- UPLOAD STAGE ---
            print("    -> Status: Uploading back to group...")
            ul_start = time.time()
            upload_success = False
            
            for attempt in range(1, 4):
                try:
                    await asyncio.wait_for(
                        client.send_file(GROUP_TARGET, local_mp4_path, caption=safe_filename, progress_callback=tracker.callback),
                        timeout=600
                    )
                    upload_success = True
                    break
                except asyncio.TimeoutError:
                    print(f"\n    [!] Upload timed out on attempt {attempt}/3. Retrying...")
                    await asyncio.sleep(10)
                except Exception as net_err:
                    err_msg = str(net_err).strip() or "Connection reset / Network drop"
                    print(f"\n    [!] Network error on upload attempt {attempt}/3: {err_msg}. Retrying शताabds: {err_msg}. Retrying...")
                    await asyncio.sleep(10)
            
            print()
            if not upload_success:
                print("    -> Upload failed after 3 attempts. Skipping log commit...")
                continue
                
            ul_time = time.time() - ul_start
            print(f"    -> Upload complete! Time taken: {ul_time:.1f} seconds.")

            if os.path.exists(local_mp4_path):
                os.remove(local_mp4_path)

            save_processed_id(message.id)
            processed_ids.add(message.id)
            session_processed_count += 1
            print(f"    -> Status: Item successfully processed and logged.")

            cooldown = random.randint(8, 15)
            print(f"    -> [Anti-Ban] Sleeping for {cooldown}s before next item...")
            await asyncio.sleep(cooldown)

        except FloodWaitError as fwe:
            print(f"\n    [!] Telegram Flood Limit hit! Forcing safety sleep for {fwe.seconds + 5} seconds...")
            await asyncio.sleep(fwe.seconds + 5)
        except Exception as e:
            print(f"\n    [!] Unexpected error: {e}. Waiting 15s to recover...")
            await asyncio.sleep(15)

    print(f"\nBatch completed safely! Total files processed this run: {session_processed_count}")

async def run_bot():
    await client.connect()
    await main()

if __name__ == "__main__":
    asyncio.run(run_bot())
