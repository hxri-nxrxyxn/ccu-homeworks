import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from portal import CoursePortal
from generator import LatexGenerator
from config import TELEGRAM_TOKEN

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

portal = CoursePortal(headless=True)
generator = LatexGenerator()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 CCU Homework HITL Bot active.\nUse /fetch to check for new assignments.")

async def fetch_assignments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="🔍 Checking portal for new assignments...")
    
    try:
        await portal.start()
        await portal.login()
        notifications = await portal.fetch_notifications(last_n_days=3)
        
        if not notifications:
            await context.bot.send_message(chat_id=chat_id, text="✅ No new assignments found.")
            return

        # For demo: take the latest one
        latest = notifications[0]
        prompt = await portal.get_assignment_prompt(latest['element'])
        context.user_data['current_prompt'] = prompt
        context.user_data['current_title'] = latest['title']

        await process_and_send(update, context, prompt)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")
    finally:
        await portal.stop()

async def process_and_send(update, context, prompt):
    chat_id = update.effective_chat.id
    title = context.user_data.get('current_title', 'Assignment')
    
    await context.bot.send_message(chat_id=chat_id, text=f"🤖 Generating LaTeX for: {title}")
    
    latex = await generator.generate_solution(prompt)
    pdf_path = generator.compile_pdf(latex, "current_solution")
    
    if pdf_path:
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve & Submit", callback_data="approve"),
                InlineKeyboardButton("🔄 Regenerate", callback_data="regenerate"),
            ],
            [InlineKeyboardButton("❌ Reject", callback_data="reject")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_document(
            chat_id=chat_id,
            document=open(pdf_path, 'rb'),
            caption=f"📝 Solution for: {title}\n\nPrompt snippet: {prompt[:200]}...",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Failed to compile PDF. Check Ollama/LaTeX status.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "approve":
        await query.edit_message_caption("📤 Submission in progress... (Waiting for page HTML implementation)")
        # TODO: Trigger portal.submit_assignment(...)
        await query.edit_message_caption("✅ Simulated Submission: Approved!")
        
    elif action == "regenerate":
        await query.edit_message_caption("🔄 Regenerating...")
        await process_and_send(update, context, context.user_data['current_prompt'])
        
    elif action == "reject":
        await query.edit_message_caption("🗑️ Rejected and discarded.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("fetch", fetch_assignments))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("Bot is running...")
    app.run_polling()
