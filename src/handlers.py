from aiogram import Router, F
from aiogram.types import ChatJoinRequest, Message
from captcha import generate_captcha
from storage import pending_requests
from db import add_user

router = Router()

@router.chat_join_request()
async def process_chat_join_request(request: ChatJoinRequest):
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    question, answer = generate_captcha()
    
    chat_username_or_id = f"@{request.chat.username}" if request.chat.username else str(chat_id)
    
    # Зберігаємо очікувану відповідь
    pending_requests[user_id] = {
        "expected_answer": answer,
        "chat_id": chat_id,
        "chat_username_or_id": chat_username_or_id,
        "attempts": 3,
        "chat_title": request.chat.title
    }
    
    text = (
        f"👋 Привіт! Ви подали заявку на вступ до чату <b>{request.chat.title}</b>.\n\n"
        f"Щоб ми переконалися, що ви не бот, будь ласка, розв'яжіть простий приклад:\n\n"
        f"Скільки буде <b>{question}</b>?\n\n"
        f"<i>Напишіть відповідь числом нижче (наприклад: 5).</i>"
    )
    
    try:
        await request.bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Failed to send message to user {user_id}: {e}")
        # Якщо бот не зміг написати, заявка ігнорується (залишається висіти, або можна відхиляти)


@router.message(F.text)
async def check_captcha_answer(message: Message):
    user_id = message.from_user.id
    
    if user_id not in pending_requests:
        return # Ігноруємо повідомлення від людей, які не подавали заявку
        
    req_data = pending_requests[user_id]
    expected_answer = req_data["expected_answer"]
    chat_id = req_data["chat_id"]
    chat_username_or_id = req_data.get("chat_username_or_id", str(chat_id))
    chat_title = req_data["chat_title"]
    attempts = req_data["attempts"]
    
    user_text = message.text.strip()
    
    if user_text.isdigit() and int(user_text) == expected_answer:
        # Відповідь правильна
        try:
            await message.bot.approve_chat_join_request(chat_id, user_id)
            await message.answer(f"✅ Відповідь правильна!\nВашу заявку до чату <b>{chat_title}</b> схвалено.", parse_mode="HTML")
            
            # Зберігаємо юзера в базу даних для майбутніх розсилок
            await add_user(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            
            # Логуємо успішний апрув для дашборду
            import aiosqlite
            from db import DB_NAME
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT INTO approvals (user_id, chat_id) VALUES (?, ?)", (user_id, chat_username_or_id))
                await db.commit()
                
        except Exception as e:
            await message.answer("❌ Сталася помилка при схваленні заявки. Зверніться до адміністратора.")
            print(f"Failed to approve request: {e}")
            
        # Видаляємо юзера зі сховища
        del pending_requests[user_id]
        
    else:
        # Відповідь неправильна
        attempts -= 1
        pending_requests[user_id]["attempts"] = attempts
        
        if attempts > 0:
            await message.answer(f"❌ Неправильно. У вас залишилося спроб: {attempts}. Спробуйте ще раз.")
        else:
            try:
                await message.bot.decline_chat_join_request(chat_id, user_id)
                await message.answer(f"🚫 Ви вичерпали всі спроби. Заявку до чату <b>{chat_title}</b> відхилено.", parse_mode="HTML")
            except Exception as e:
                print(f"Failed to decline request: {e}")
                
            del pending_requests[user_id]
