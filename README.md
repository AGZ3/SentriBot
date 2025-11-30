<p align="left">
   <img src="sentribot_logo.png" alt="SentriBot logo" width="120"/>
</p>

# SentriBot

A Discord bot that uses AI to automatically detect and quarantine spam, phishing, and malicious messages in real-time.

## What It Does

- **AI-Powered Detection**: Uses a fine-tuned DistilBERT model to classify messages as spam/phishing
- **Auto-Quarantine**: Deletes suspicious messages and sends them to moderators for review
- **Moderator Review**: Mods can approve (✅) or reject (❌) flagged messages via reactions
- **Domain Whitelist**: Trusted domains (YouTube, Discord, GitHub, DeviantArt) bypass detection
- **User Notifications**: Warns users when their message is under review

## What We Built

1. **Model Training**: Fine-tuned DistilBERT on the `wangyuancheng/discord-phishing-scam` dataset
   - Binary classification (legitimate vs spam/phishing)
   - Trained with 128 token max length, batch size 16, 30 epochs
   - Achieved high accuracy on Discord-specific phishing patterns

2. **Discord Bot**: Integrated the trained model with Discord.py
   - Real-time message inference
   - Moderator review workflow with reactions
   - Admin commands for configuration
   - Permission handling and error recovery

## Quick Setup

### Prerequisites
- Python 3.8+
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))

### Installation

1. **Clone and navigate to the project**
   ```bash
   cd SentriBot
   ```

2. **Create virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Train and export the model OR Direct download**
   
   Open and run all cells in `SentryBot_Model.ipynb`:
   ```bash
   jupyter notebook SentryBot_Model.ipynb
   ```
   
   This will:
   - Download the discord-phishing-scam dataset
   - Fine-tune DistilBERT on spam/phishing detection
   - Save the trained model to `./phishing_detection_model/`
   - Rename the folder to `discord_scam_model/` if needed

   --- 

   To download the model without training yourself, use the following link:
   https://drive.google.com/drive/folders/1vbXaIjQCOy9U3QHLgps2N9F9o22tY4Dj?usp=sharing

4. **Set up environment variables**
   
   Create a `.env` file:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

5. **Run the bot**
   ```bash
   python bot.py
   ```

### Bot Setup

1. Invite the bot to your server with `Manage Messages` permission
2. Run `!reviewchannel <channel_id>` to set the moderation review channel
3. Type `!help` to see all commands

## Commands

- `!help` - Display help menu
- `!reviewchannel <channel_id>` - Set mod review channel (Admin only)

## Model Files

The trained model is in `discord_scam_model/` and includes:
- `model.safetensors` - Model weights
- `config.json` - Model configuration
- Tokenizer files (`vocab.txt`, `tokenizer.json`, etc.)

## Technologies

- **Discord.py** - Discord API wrapper
- **Transformers** - Hugging Face model library
- **PyTorch** - Deep learning framework
- **DistilBERT** - Lightweight BERT model for text classification
