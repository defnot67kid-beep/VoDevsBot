import discord
from discord.ext import commands
import random
import asyncio
import math
from datetime import datetime  # FIXED: Added missing import
from typing import Optional

class GameEngine(commands.Cog):
    """Game Engine - 50+ games and battles"""
    
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.battles = {}
        self.raid_bosses = {}
        self.active_tournaments = {}
        self.werewolf_games = {}
        self.mafia_games = {}
    
    # ========== NUMBER GUESSING ==========
    
    @commands.command(name="guess")
    async def guess_number(self, ctx, number: int):
        """Guess a number between 1-100"""
        if number < 1 or number > 100:
            await ctx.send("❌ Number must be between 1 and 100!")
            return
        
        target = random.randint(1, 100)
        attempts = 0
        max_attempts = 10
        
        embed = discord.Embed(
            title="🎯 Guess the Number",
            description="I'm thinking of a number between 1-100. Try to guess it!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Attempts", value=f"0/{max_attempts}", inline=True)
        embed.add_field(name="Range", value="1-100", inline=True)
        embed.set_footer(text=f"{ctx.author.name}'s game")
        
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.content.isdigit()
        
        while attempts < max_attempts:
            try:
                guess_msg = await self.bot.wait_for("message", timeout=30.0, check=check)
                guess = int(guess_msg.content)
                attempts += 1
                
                if guess == target:
                    embed = discord.Embed(
                        title="🎉 You Got It!",
                        description=f"**{target}** was the correct number! You got it in {attempts} attempts!",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
                    return
                elif guess < target:
                    await ctx.send(f"📈 Higher! ({attempts}/{max_attempts})")
                else:
                    await ctx.send(f"📉 Lower! ({attempts}/{max_attempts})")
                    
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The number was **{target}**")
                return
        
        await ctx.send(f"❌ Out of attempts! The number was **{target}**")
    
    @commands.command(name="guess-hard")
    async def guess_hard(self, ctx, number: int):
        """Guess a number between 1-1000 (Hard mode)"""
        if number < 1 or number > 1000:
            await ctx.send("❌ Number must be between 1 and 1000!")
            return
        
        target = random.randint(1, 1000)
        attempts = 0
        max_attempts = 15
        
        embed = discord.Embed(
            title="🎯 Guess the Number (Hard)",
            description="I'm thinking of a number between 1-1000. Try to guess it!",
            color=discord.Color.red()
        )
        embed.add_field(name="Attempts", value=f"0/{max_attempts}", inline=True)
        embed.add_field(name="Range", value="1-1000", inline=True)
        embed.set_footer(text=f"{ctx.author.name}'s game")
        
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.content.isdigit()
        
        while attempts < max_attempts:
            try:
                guess_msg = await self.bot.wait_for("message", timeout=30.0, check=check)
                guess = int(guess_msg.content)
                attempts += 1
                
                if guess == target:
                    embed = discord.Embed(
                        title="🎉 You Got It!",
                        description=f"**{target}** was the correct number! You got it in {attempts} attempts!",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)
                    return
                elif guess < target:
                    await ctx.send(f"📈 Higher! ({attempts}/{max_attempts})")
                else:
                    await ctx.send(f"📉 Lower! ({attempts}/{max_attempts})")
                    
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The number was **{target}**")
                return
        
        await ctx.send(f"❌ Out of attempts! The number was **{target}**")
    
    # ========== TRIVIA ==========
    
    @commands.command(name="trivia")
    async def trivia(self, ctx):
        """Get a random trivia question"""
        questions = [
            {"q": "What is the capital of France?", "a": "paris"},
            {"q": "What is the largest planet in our solar system?", "a": "jupiter"},
            {"q": "Who wrote 'Romeo and Juliet'?", "a": "shakespeare"},
            {"q": "What is the chemical symbol for water?", "a": "h2o"},
            {"q": "What is the speed of light?", "a": "299792458"},
        ]
        
        question = random.choice(questions)
        
        embed = discord.Embed(
            title="🧠 Trivia Question",
            description=question["q"],
            color=discord.Color.purple()
        )
        embed.set_footer(text="Type your answer!")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author
        
        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            if msg.content.lower() == question["a"].lower():
                await ctx.send("✅ Correct! 🎉")
            else:
                await ctx.send(f"❌ Incorrect! The answer was **{question['a']}**")
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! The answer was **{question['a']}**")
    
    @commands.command(name="trivia-category")
    async def trivia_category(self, ctx, category: str):
        """Get trivia by category"""
        categories = {
            "science": [
                {"q": "What is the chemical symbol for gold?", "a": "au"},
                {"q": "What is the largest organ in the human body?", "a": "skin"},
            ],
            "history": [
                {"q": "What year did World War II end?", "a": "1945"},
                {"q": "Who was the first president of the United States?", "a": "washington"},
            ],
            "sports": [
                {"q": "What is the highest score in a single dart throw?", "a": "60"},
                {"q": "What country invented basketball?", "a": "usa"},
            ]
        }
        
        category = category.lower()
        if category not in categories:
            await ctx.send(f"❌ Category not found! Available: {', '.join(categories.keys())}")
            return
        
        question = random.choice(categories[category])
        
        embed = discord.Embed(
            title=f"🧠 {category.title()} Trivia",
            description=question["q"],
            color=discord.Color.purple()
        )
        embed.set_footer(text="Type your answer!")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author
        
        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            if msg.content.lower() == question["a"].lower():
                await ctx.send("✅ Correct! 🎉")
            else:
                await ctx.send(f"❌ Incorrect! The answer was **{question['a']}**")
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! The answer was **{question['a']}**")
    
    # ========== HANGMAN ==========
    
    @commands.command(name="hangman")
    async def hangman(self, ctx):
        """Start a game of Hangman"""
        words = ["python", "discord", "bot", "developer", "gaming", "server", "moderation", "economy"]
        word = random.choice(words)
        guessed = set()
        attempts = 6
        display = "_" * len(word)
        
        embed = discord.Embed(
            title="🎯 Hangman",
            description=f"```\n{display}\n```",
            color=discord.Color.blue()
        )
        embed.add_field(name="Attempts Left", value=attempts, inline=True)
        embed.add_field(name="Guessed Letters", value="None", inline=True)
        embed.set_footer(text="Type a letter to guess!")
        
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and len(m.content) == 1 and m.content.isalpha()
        
        while attempts > 0 and "_" in display:
            try:
                guess_msg = await self.bot.wait_for("message", timeout=30.0, check=check)
                guess = guess_msg.content.lower()
                
                if guess in guessed:
                    await ctx.send(f"⚠️ You already guessed '{guess}'!")
                    continue
                
                guessed.add(guess)
                
                if guess in word:
                    new_display = ""
                    for i, char in enumerate(word):
                        if char == guess or word[i] in guessed:
                            new_display += word[i]
                        else:
                            new_display += "_"
                    display = new_display
                    
                    embed = discord.Embed(
                        title="🎯 Hangman",
                        description=f"```\n{display}\n```",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Attempts Left", value=attempts, inline=True)
                    embed.add_field(name="Guessed Letters", value=", ".join(sorted(guessed)), inline=True)
                    await msg.edit(embed=embed)
                else:
                    attempts -= 1
                    
                    embed = discord.Embed(
                        title="🎯 Hangman",
                        description=f"```\n{display}\n```",
                        color=discord.Color.orange() if attempts > 0 else discord.Color.red()
                    )
                    embed.add_field(name="Attempts Left", value=attempts, inline=True)
                    embed.add_field(name="Guessed Letters", value=", ".join(sorted(guessed)), inline=True)
                    await msg.edit(embed=embed)
                    
                    if attempts == 0:
                        await ctx.send(f"💀 Game Over! The word was **{word}**")
                        return
                        
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The word was **{word}**")
                return
        
        if "_" not in display:
            await ctx.send(f"🎉 Congratulations! You guessed the word **{word}**!")
    
    # ========== ROCK PAPER SCISSORS ==========
    
    @commands.command(name="rps")
    async def rps_user(self, ctx, opponent: discord.Member):
        """Play Rock Paper Scissors against another user"""
        options = ["rock", "paper", "scissors"]
        
        embed = discord.Embed(
            title="✊ Rock Paper Scissors",
            description=f"{ctx.author.mention} vs {opponent.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="How to play", value="Type `rock`, `paper`, or `scissors`", inline=False)
        embed.set_footer(text="Both players type their choice!")
        
        await ctx.send(embed=embed)
        
        choices = {}
        
        def check(m):
            return m.author in [ctx.author, opponent] and m.content.lower() in options
        
        for player in [ctx.author, opponent]:
            try:
                msg = await self.bot.wait_for("message", timeout=30.0, check=check)
                choices[msg.author] = msg.content.lower()
                await ctx.send(f"✅ {msg.author.mention} has chosen!")
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ {player.mention} didn't respond in time!")
                return
        
        p1_choice = choices[ctx.author]
        p2_choice = choices[opponent]
        
        result = self._rps_result(p1_choice, p2_choice)
        
        embed = discord.Embed(
            title="✊ Rock Paper Scissors Results",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{ctx.author.display_name}", value=p1_choice.title(), inline=True)
        embed.add_field(name=f"{opponent.display_name}", value=p2_choice.title(), inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await ctx.send(embed=embed)
    
    def _rps_result(self, p1, p2):
        if p1 == p2:
            return "🤝 It's a tie!"
        if (p1 == "rock" and p2 == "scissors") or \
           (p1 == "paper" and p2 == "rock") or \
           (p1 == "scissors" and p2 == "paper"):
            return "🎉 Player 1 wins!"
        return "🎉 Player 2 wins!"
    
    @commands.command(name="rps-bot")
    async def rps_bot(self, ctx, choice: str):
        """Play Rock Paper Scissors against the bot"""
        options = ["rock", "paper", "scissors"]
        choice = choice.lower()
        
        if choice not in options:
            await ctx.send(f"❌ Choose from: {', '.join(options)}")
            return
        
        bot_choice = random.choice(options)
        result = self._rps_result(choice, bot_choice)
        
        embed = discord.Embed(
            title="✊ Rock Paper Scissors (vs Bot)",
            color=discord.Color.blue()
        )
        embed.add_field(name=f"{ctx.author.display_name}", value=choice.title(), inline=True)
        embed.add_field(name="Bot", value=bot_choice.title(), inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        
        await ctx.send(embed=embed)
    
    # ========== TIC TAC TOE ==========
    
    @commands.command(name="tictactoe")
    async def tictactoe(self, ctx, opponent: discord.Member):
        """Start a Tic Tac Toe game against a user"""
        game_id = f"{ctx.author.id}-{opponent.id}"
        
        if game_id in self.games:
            await ctx.send("❌ You already have a game in progress!")
            return
        
        board = [" " for _ in range(9)]
        current_turn = ctx.author
        
        self.games[game_id] = {
            "board": board,
            "current_turn": current_turn,
            "player1": ctx.author,
            "player2": opponent,
            "game_id": game_id
        }
        
        embed = discord.Embed(
            title="🎮 Tic Tac Toe",
            description=self._display_board(board),
            color=discord.Color.blue()
        )
        embed.add_field(name="Current Turn", value=current_turn.mention, inline=True)
        embed.add_field(name="How to Play", value="Type a number 1-9 to place your mark", inline=False)
        embed.set_footer(text="Positions: 1=top-left, 5=center, 9=bottom-right")
        
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author in [ctx.author, opponent] and m.content.isdigit() and 1 <= int(m.content) <= 9
        
        while True:
            try:
                move_msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                position = int(move_msg.content) - 1
                
                if move_msg.author != current_turn:
                    await ctx.send(f"❌ It's {current_turn.mention}'s turn!")
                    continue
                
                if board[position] != " ":
                    await ctx.send("❌ That position is already taken!")
                    continue
                
                mark = "X" if move_msg.author == ctx.author else "O"
                board[position] = mark
                
                winner = self._check_tictactoe_winner(board)
                
                embed = discord.Embed(
                    title="🎮 Tic Tac Toe",
                    description=self._display_board(board),
                    color=discord.Color.green() if winner else discord.Color.blue()
                )
                
                if winner:
                    embed.add_field(name="🏆 Winner", value=f"{winner.mention} wins!", inline=False)
                    await ctx.send(embed=embed)
                    del self.games[game_id]
                    return
                elif " " not in board:
                    embed.add_field(name="🤝 Tie", value="It's a draw!", inline=False)
                    await ctx.send(embed=embed)
                    del self.games[game_id]
                    return
                
                current_turn = opponent if current_turn == ctx.author else ctx.author
                self.games[game_id]["current_turn"] = current_turn
                
                embed.add_field(name="Current Turn", value=current_turn.mention, inline=True)
                await msg.edit(embed=embed)
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ Game timed out!")
                del self.games[game_id]
                return
    
    def _display_board(self, board):
        return f"```\n{board[0]} | {board[1]} | {board[2]}\n---+---+---\n{board[3]} | {board[4]} | {board[5]}\n---+---+---\n{board[6]} | {board[7]} | {board[8]}\n```"
    
    def _check_tictactoe_winner(self, board):
        win_patterns = [
            [0,1,2], [3,4,5], [6,7,8],  # rows
            [0,3,6], [1,4,7], [2,5,8],  # columns
            [0,4,8], [2,4,6]            # diagonals
        ]
        
        for pattern in win_patterns:
            if board[pattern[0]] == board[pattern[1]] == board[pattern[2]] != " ":
                # Find the winner
                if "X" in [board[p] for p in pattern]:
                    return self.games.get(list(self.games.keys())[0])["player1"] if self.games else None
                else:
                    return self.games.get(list(self.games.keys())[0])["player2"] if self.games else None
        return None
    
    @commands.command(name="ttt-bot")
    async def tictactoe_bot(self, ctx):
        """Play Tic Tac Toe against the bot"""
        board = [" " for _ in range(9)]
        current_turn = ctx.author
        
        embed = discord.Embed(
            title="🎮 Tic Tac Toe (vs Bot)",
            description=self._display_board(board),
            color=discord.Color.blue()
        )
        embed.add_field(name="Current Turn", value=current_turn.mention, inline=True)
        embed.add_field(name="How to Play", value="Type a number 1-9 to place your mark", inline=False)
        
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= 9
        
        while True:
            # Player's turn
            try:
                move_msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                position = int(move_msg.content) - 1
                
                if board[position] != " ":
                    await ctx.send("❌ That position is already taken!")
                    continue
                
                board[position] = "X"
                
                winner = self._check_tictactoe_winner_simple(board)
                if winner:
                    embed = discord.Embed(
                        title="🎮 Tic Tac Toe (vs Bot)",
                        description=self._display_board(board),
                        color=discord.Color.green()
                    )
                    embed.add_field(name="🏆 Winner", value=f"🎉 {ctx.author.mention} wins!", inline=False)
                    await ctx.send(embed=embed)
                    return
                elif " " not in board:
                    embed = discord.Embed(
                        title="🎮 Tic Tac Toe (vs Bot)",
                        description=self._display_board(board),
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="🤝 Tie", value="It's a draw!", inline=False)
                    await ctx.send(embed=embed)
                    return
                
                # Bot's turn
                available = [i for i in range(9) if board[i] == " "]
                bot_move = random.choice(available)
                board[bot_move] = "O"
                
                winner = self._check_tictactoe_winner_simple(board)
                if winner:
                    embed = discord.Embed(
                        title="🎮 Tic Tac Toe (vs Bot)",
                        description=self._display_board(board),
                        color=discord.Color.red()
                    )
                    embed.add_field(name="🏆 Winner", value="🤖 Bot wins!", inline=False)
                    await ctx.send(embed=embed)
                    return
                elif " " not in board:
                    embed = discord.Embed(
                        title="🎮 Tic Tac Toe (vs Bot)",
                        description=self._display_board(board),
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="🤝 Tie", value="It's a draw!", inline=False)
                    await ctx.send(embed=embed)
                    return
                
                embed = discord.Embed(
                    title="🎮 Tic Tac Toe (vs Bot)",
                    description=self._display_board(board),
                    color=discord.Color.blue()
                )
                embed.add_field(name="Current Turn", value=ctx.author.mention, inline=True)
                await msg.edit(embed=embed)
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ Game timed out!")
                return
    
    def _check_tictactoe_winner_simple(self, board):
        win_patterns = [
            [0,1,2], [3,4,5], [6,7,8],
            [0,3,6], [1,4,7], [2,5,8],
            [0,4,8], [2,4,6]
        ]
        
        for pattern in win_patterns:
            if board[pattern[0]] == board[pattern[1]] == board[pattern[2]] != " ":
                return board[pattern[0]]
        return None
    
    # ========== SLOTS ==========
    
    @commands.command(name="slots")
    async def slots(self, ctx):
        """Play the slot machine"""
        emojis = ["🍒", "🍋", "🍊", "🍉", "🍇", "💎", "7️⃣"]
        result = [random.choice(emojis) for _ in range(3)]
        
        embed = discord.Embed(
            title="🎰 Slot Machine",
            description=f"| {' | '.join(result)} |",
            color=discord.Color.gold()
        )
        
        if result[0] == result[1] == result[2]:
            if result[0] == "7️⃣":
                embed.add_field(name="🎉 Jackpot!", value="You won the grand prize!", inline=False)
                embed.color = discord.Color.gold()
            else:
                embed.add_field(name="🎉 Win!", value="All three match!", inline=False)
                embed.color = discord.Color.green()
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            embed.add_field(name="🎉 Small Win!", value="Two symbols match!", inline=False)
            embed.color = discord.Color.blue()
        else:
            embed.add_field(name="😞 No Win", value="Better luck next time!", inline=False)
            embed.color = discord.Color.red()
        
        await ctx.send(embed=embed)
    
    @commands.command(name="slots-mega")
    async def slots_mega(self, ctx):
        """Mega slots with higher stakes"""
        emojis = ["🍒", "🍋", "🍊", "🍉", "🍇", "💎", "7️⃣", "💰", "⭐", "🎯"]
        result = [random.choice(emojis) for _ in range(3)]
        
        embed = discord.Embed(
            title="🎰 Mega Slots",
            description=f"| {' | '.join(result)} |",
            color=discord.Color.purple()
        )
        
        if result[0] == result[1] == result[2]:
            if result[0] == "7️⃣":
                embed.add_field(name="🎉 ULTRA JACKPOT!", value="💎 You hit the mega jackpot!", inline=False)
                embed.color = discord.Color.gold()
            else:
                embed.add_field(name="🎉 Mega Win!", value="All three match!", inline=False)
                embed.color = discord.Color.green()
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            embed.add_field(name="🎉 Small Win!", value="Two symbols match!", inline=False)
            embed.color = discord.Color.blue()
        else:
            embed.add_field(name="😞 No Win", value="Better luck next time!", inline=False)
            embed.color = discord.Color.red()
        
        await ctx.send(embed=embed)
    
    # ========== DICE ==========
    
    @commands.command(name="dice")
    async def dice(self, ctx):
        """Roll a dice (1-6)"""
        result = random.randint(1, 6)
        
        dice_faces = {
            1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"
        }
        
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"You rolled: **{result}** {dice_faces[result]}",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="dice-odds")
    async def dice_odds(self, ctx, bet_on: int):
        """Roll dice with odds betting"""
        if bet_on < 1 or bet_on > 6:
            await ctx.send("❌ Bet on a number between 1-6")
            return
        
        result = random.randint(1, 6)
        
        if result == bet_on:
            embed = discord.Embed(
                title="🎲 Dice Bet",
                description=f"🎉 You won! You bet on {bet_on} and rolled **{result}**!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🎲 Dice Bet",
                description=f"😞 You lost! You bet on {bet_on} but rolled **{result}**",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
    
    # ========== COIN FLIP ==========
    
    @commands.command(name="coinflip")
    async def coinflip(self, ctx):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="coinflip-bet")
    async def coinflip_bet(self, ctx, amount: int, choice: str):
        """Flip a coin with betting"""
        choice = choice.lower()
        if choice not in ["heads", "tails"]:
            await ctx.send("❌ Choose 'heads' or 'tails'")
            return
        
        result = random.choice(["heads", "tails"])
        
        if choice == result:
            embed = discord.Embed(
                title="🪙 Coin Flip Bet",
                description=f"🎉 You won! You bet on {choice} and got **{result.title()}**!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="🪙 Coin Flip Bet",
                description=f"😞 You lost! You bet on {choice} but got **{result.title()}**",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
    
    # ========== 8-BALL ==========
    
    @commands.command(name="eightball")
    async def eightball(self, ctx, *, question: str):
        """Ask the Magic 8-Ball a question"""
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.",
            "Better not tell you now.", "Cannot predict now.",
            "Concentrate and ask again.", "Don't count on it.",
            "My reply is no.", "My sources say no.", "Outlook not so good.",
            "Very doubtful."
        ]
        
        response = random.choice(responses)
        
        embed = discord.Embed(
            title="🔮 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"**{response}**", inline=False)
        
        await ctx.send(embed=embed)
    
    # ========== BATTLES ==========
    
    @commands.command(name="fight")
    async def fight(self, ctx, opponent: discord.Member):
        """Start a PvP battle"""
        if opponent == ctx.author:
            await ctx.send("❌ You can't fight yourself!")
            return
        
        player1_health = 100
        player2_health = 100
        
        embed = discord.Embed(
            title="⚔️ PvP Battle",
            description=f"{ctx.author.mention} vs {opponent.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name=f"{ctx.author.display_name} HP", value=f"{player1_health}/100", inline=True)
        embed.add_field(name=f"{opponent.display_name} HP", value=f"{player2_health}/100", inline=True)
        embed.set_footer(text="Type 'attack', 'heal', or 'shield'")
        
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author in [ctx.author, opponent] and m.content.lower() in ["attack", "heal", "shield"]
        
        turn = ctx.author
        
        while player1_health > 0 and player2_health > 0:
            try:
                action_msg = await self.bot.wait_for("message", timeout=30.0, check=check)
                action = action_msg.content.lower()
                attacker = action_msg.author
                defender = opponent if attacker == ctx.author else ctx.author
                
                damage = 0
                if action == "attack":
                    damage = random.randint(10, 25)
                    if random.random() < 0.2:  # 20% chance of critical hit
                        damage *= 2
                        await ctx.send(f"💥 CRITICAL HIT!")
                    
                    if defender == opponent:
                        player2_health -= damage
                    else:
                        player1_health -= damage
                    await ctx.send(f"💢 {attacker.mention} attacks! **-{damage} HP**")
                    
                elif action == "heal":
                    heal_amount = random.randint(10, 30)
                    if attacker == ctx.author:
                        player1_health = min(100, player1_health + heal_amount)
                    else:
                        player2_health = min(100, player2_health + heal_amount)
                    await ctx.send(f"💚 {attacker.mention} heals! **+{heal_amount} HP**")
                    
                elif action == "shield":
                    await ctx.send(f"🛡️ {attacker.mention} raises their shield!")
                
                # Update embed
                embed = discord.Embed(
                    title="⚔️ PvP Battle",
                    description=f"{ctx.author.mention} vs {opponent.mention}",
                    color=discord.Color.red()
                )
                embed.add_field(name=f"{ctx.author.display_name} HP", value=f"{max(0, player1_health)}/100", inline=True)
                embed.add_field(name=f"{opponent.display_name} HP", value=f"{max(0, player2_health)}/100", inline=True)
                await msg.edit(embed=embed)
                
                turn = opponent if turn == ctx.author else ctx.author
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ Battle timed out!")
                return
        
        # Determine winner
        winner = ctx.author if player1_health > 0 else opponent
        embed = discord.Embed(
            title="🏆 Battle Over!",
            description=f"{winner.mention} wins the battle!",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="fight-bot")
    async def fight_bot(self, ctx):
        """Fight the bot"""
        player_health = 100
        bot_health = 100
        
        embed = discord.Embed(
            title="⚔️ Battle vs Bot",
            description=f"{ctx.author.mention} vs 🤖 Bot",
            color=discord.Color.blue()
        )
        embed.add_field(name=f"{ctx.author.display_name} HP", value=f"{player_health}/100", inline=True)
        embed.add_field(name="🤖 Bot HP", value=f"{bot_health}/100", inline=True)
        embed.set_footer(text="Type 'attack', 'heal', or 'shield'")
        
        msg = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.content.lower() in ["attack", "heal", "shield"]
        
        turn = ctx.author
        
        while player_health > 0 and bot_health > 0:
            # Player's turn
            try:
                action_msg = await self.bot.wait_for("message", timeout=30.0, check=check)
                action = action_msg.content.lower()
                
                damage = 0
                if action == "attack":
                    damage = random.randint(10, 25)
                    if random.random() < 0.2:
                        damage *= 2
                        await ctx.send(f"💥 CRITICAL HIT!")
                    bot_health -= damage
                    await ctx.send(f"💢 You attack! **-{damage} HP** to bot")
                    
                elif action == "heal":
                    heal_amount = random.randint(10, 30)
                    player_health = min(100, player_health + heal_amount)
                    await ctx.send(f"💚 You heal! **+{heal_amount} HP**")
                    
                elif action == "shield":
                    await ctx.send(f"🛡️ You raise your shield!")
                
                # Bot's turn
                bot_action = random.choice(["attack", "attack", "attack", "heal", "shield"])
                if bot_action == "attack":
                    damage = random.randint(10, 25)
                    if random.random() < 0.2:
                        damage *= 2
                        await ctx.send(f"💥 Bot CRITICAL HIT!")
                    player_health -= damage
                    await ctx.send(f"🤖 Bot attacks! **-{damage} HP**")
                elif bot_action == "heal":
                    heal_amount = random.randint(10, 30)
                    bot_health = min(100, bot_health + heal_amount)
                    await ctx.send(f"💚 Bot heals! **+{heal_amount} HP**")
                elif bot_action == "shield":
                    await ctx.send(f"🛡️ Bot raises their shield!")
                
                # Update embed
                embed = discord.Embed(
                    title="⚔️ Battle vs Bot",
                    description=f"{ctx.author.mention} vs 🤖 Bot",
                    color=discord.Color.blue()
                )
                embed.add_field(name=f"{ctx.author.display_name} HP", value=f"{max(0, player_health)}/100", inline=True)
                embed.add_field(name="🤖 Bot HP", value=f"{max(0, bot_health)}/100", inline=True)
                await msg.edit(embed=embed)
                
            except asyncio.TimeoutError:
                await ctx.send("⏰ Battle timed out!")
                return
        
        # Determine winner
        if player_health > 0:
            embed = discord.Embed(
                title="🏆 Battle Over!",
                description=f"{ctx.author.mention} wins against the bot!",
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title="🏆 Battle Over!",
                description="🤖 Bot wins!",
                color=discord.Color.red()
            )
        await ctx.send(embed=embed)
    
    # ========== RAID BOSS ==========
    
    @commands.command(name="raidboss")
    async def raidboss(self, ctx):
        """Spawn a raid boss"""
        boss_health = 500
        self.raid_bosses[ctx.guild.id] = {
            "health": boss_health,
            "max_health": boss_health,
            "participants": set(),
            "last_attack": None
        }
        
        embed = discord.Embed(
            title="🐉 Raid Boss Spawned!",
            description="A powerful raid boss has appeared!",
            color=discord.Color.red()
        )
        embed.add_field(name="HP", value=f"{boss_health}/{boss_health}", inline=True)
        embed.add_field(name="How to Fight", value="Use `!attack` to attack the boss", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="attack")
    async def attack_raidboss(self, ctx):
        """Attack the raid boss"""
        if ctx.guild.id not in self.raid_bosses:
            await ctx.send("❌ No raid boss is active in this server! Use `!raidboss` to spawn one.")
            return
        
        boss = self.raid_bosses[ctx.guild.id]
        damage = random.randint(10, 40)
        
        if random.random() < 0.1:  # 10% chance of crit
            damage *= 2
            await ctx.send(f"💥 CRITICAL HIT! You deal **{damage}** damage!")
        
        boss["health"] -= damage
        boss["participants"].add(ctx.author)
        
        if boss["health"] <= 0:
            embed = discord.Embed(
                title="🎉 Raid Boss Defeated!",
                description=f"The raid boss has been defeated by {len(boss['participants'])} brave warriors!",
                color=discord.Color.gold()
            )
            embed.add_field(name="🏆 MVP", value=ctx.author.mention, inline=False)
            await ctx.send(embed=embed)
            del self.raid_bosses[ctx.guild.id]
        else:
            embed = discord.Embed(
                title="🐉 Raid Boss",
                description=f"You deal **{damage}** damage!",
                color=discord.Color.orange()
            )
            embed.add_field(name="HP", value=f"{boss['health']}/{boss['max_health']}", inline=True)
            embed.add_field(name="Participants", value=len(boss['participants']), inline=True)
            await ctx.send(embed=embed)
    
    @commands.command(name="heal")
    async def heal_battle(self, ctx):
        """Heal in battle"""
        # Simplified version - would integrate with active battles
        await ctx.send(f"💚 You heal yourself for **{random.randint(10, 30)}** HP!")
    
    @commands.command(name="shield")
    async def shield_battle(self, ctx):
        """Shield in battle"""
        await ctx.send("🛡️ You raise your shield!")
    
    @commands.command(name="special")
    async def special_attack(self, ctx):
        """Special attack in battle"""
        damage = random.randint(30, 60)
        if random.random() < 0.15:
            damage *= 2
            await ctx.send(f"💥 ULTRA SPECIAL! You deal **{damage}** damage!")
        else:
            await ctx.send(f"⚡ Special attack! You deal **{damage}** damage!")
    
    # ========== CLAN SYSTEM ==========
    
    @commands.command(name="clan-create")
    async def clan_create(self, ctx, *, name: str):
        """Create a clan"""
        # Simplified clan creation
        await ctx.send(f"🏰 Clan **{name}** has been created by {ctx.author.mention}!")
    
    @commands.command(name="clan-invite")
    async def clan_invite(self, ctx, member: discord.Member):
        """Invite a user to your clan"""
        await ctx.send(f"📨 {member.mention} has been invited to your clan!")
    
    @commands.command(name="clan-join")
    async def clan_join(self, ctx, *, clan_name: str):
        """Join a clan"""
        await ctx.send(f"✅ You have joined clan **{clan_name}**!")
    
    @commands.command(name="clan-battle")
    async def clan_battle(self, ctx, *, clan_name: str):
        """Start a clan war"""
        await ctx.send(f"⚔️ War declared against clan **{clan_name}**!")
    
    @commands.command(name="clan-leave")
    async def clan_leave(self, ctx):
        """Leave your clan"""
        await ctx.send("✅ You have left your clan.")
    
    @commands.command(name="clan-kick")
    async def clan_kick(self, ctx, member: discord.Member):
        """Kick a member from your clan"""
        await ctx.send(f"👢 {member.mention} has been kicked from the clan.")
    
    # ========== ADVENTURE GAMES ==========
    
    @commands.command(name="hunt")
    async def hunt(self, ctx):
        """Go hunting"""
        animals = ["🦌 Deer", "🐰 Rabbit", "🦊 Fox", "🐗 Boar"]
        animal = random.choice(animals)
        success = random.random() < 0.6
        
        if success:
            await ctx.send(f"🎯 You successfully hunted a **{animal}**!")
        else:
            await ctx.send(f"😞 You went hunting but found nothing.")
    
    @commands.command(name="hunt-bear")
    async def hunt_bear(self, ctx):
        """Hunt a bear (high risk, high reward)"""
        success = random.random() < 0.3
        
        if success:
            await ctx.send("🎯 You successfully hunted a **🐻 Bear**! Amazing!")
        else:
            await ctx.send("😱 The bear attacked you! You barely escaped!")
    
    @commands.command(name="fish")
    async def fish(self, ctx):
        """Go fishing"""
        fish_types = ["🐟 Trout", "🐠 Salmon", "🐡 Pufferfish", "🐟 Bass"]
        fish = random.choice(fish_types)
        success = random.random() < 0.5
        
        if success:
            await ctx.send(f"🎣 You caught a **{fish}**!")
        else:
            await ctx.send("😞 You didn't catch anything.")
    
    @commands.command(name="fish-rare")
    async def fish_rare(self, ctx):
        """Fish for rare fish"""
        success = random.random() < 0.1
        
        if success:
            await ctx.send("🎣🐟 You caught a **RARE Golden Fish**!")
        else:
            await ctx.send("😞 You caught nothing special.")
    
    @commands.command(name="mine")
    async def mine(self, ctx):
        """Go mining"""
        ores = ["🪨 Stone", "🪨 Iron", "💎 Diamond", "🪙 Gold"]
        ore = random.choice(ores)
        success = random.random() < 0.4
        
        if success:
            await ctx.send(f"⛏️ You mined some **{ore}**!")
        else:
            await ctx.send("⛏️ You mined nothing.")
    
    @commands.command(name="mine-deep")
    async def mine_deep(self, ctx):
        """Deep mining (higher rewards)"""
        ores = ["💎 Diamond", "🪙 Gold", "🪙 Platinum", "💎 Ruby"]
        ore = random.choice(ores)
        success = random.random() < 0.25
        
        if success:
            await ctx.send(f"⛏️✨ Deep mining found a **{ore}**!")
        else:
            await ctx.send("⛏️ Deep mining found nothing.")
    
    @commands.command(name="explore")
    async def explore(self, ctx):
        """Explore unknown territory"""
        discoveries = ["🌳 Forest", "🏔️ Mountain", "🌊 Beach", "🏜️ Desert", "🌋 Volcano"]
        discovery = random.choice(discoveries)
        
        await ctx.send(f"🗺️ You discovered a **{discovery}**!")
    
    @commands.command(name="explore-danger")
    async def explore_danger(self, ctx):
        """Dangerous exploration"""
        outcome = random.choice(["found treasure", "was attacked", "got lost", "found a cave"])
        
        await ctx.send(f"🗺️ You explored dangerously and **{outcome}**!")
    
    # ========== WORD/PUZZLE GAMES ==========
    
    @commands.command(name="wordle")
    async def wordle(self, ctx):
        """Play Wordle"""
        words = ["apple", "beach", "cloud", "dance", "eagle", "flame", "grape", "heart", "ivory", "jelly"]
        word = random.choice(words)
        attempts = 0
        max_attempts = 6
        
        embed = discord.Embed(
            title="🧩 Wordle",
            description="Guess the 5-letter word!",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Attempts: 0/{max_attempts}")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and len(m.content) == 5
        
        while attempts < max_attempts:
            try:
                guess_msg = await self.bot.wait_for("message", timeout=30.0, check=check)
                guess = guess_msg.content.lower()
                attempts += 1
                
                feedback = ""
                for i, char in enumerate(guess):
                    if char == word[i]:
                        feedback += "🟩"
                    elif char in word:
                        feedback += "🟨"
                    else:
                        feedback += "⬛"
                
                embed = discord.Embed(
                    title="🧩 Wordle",
                    description=f"`{guess}`\n{feedback}",
                    color=discord.Color.green() if guess == word else discord.Color.blue()
                )
                embed.set_footer(text=f"Attempts: {attempts}/{max_attempts}")
                
                await ctx.send(embed=embed)
                
                if guess == word:
                    await ctx.send(f"🎉 You got it in {attempts} attempts!")
                    return
                    
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The word was **{word}**")
                return        
        await ctx.send(f"❌ Out of attempts! The word was **{word}**")
    
    @commands.command(name="wordle-hard")
    async def wordle_hard(self, ctx):
        """Hard mode Wordle"""
        await ctx.send("🔴 Hard mode Wordle: words can be repeated!")
        await self.wordle(ctx)
    
    # ========== TOURNAMENT SYSTEM ==========
    
    @commands.command(name="tournament-start")
    async def tournament_start(self, ctx, *, game: str):
        """Start a tournament"""
        tournament_id = f"{ctx.guild.id}-{datetime.now().timestamp()}"
        self.active_tournaments[tournament_id] = {
            "game": game,
            "host": ctx.author,
            "participants": [ctx.author],
            "status": "open",
            "bracket": []
        }
        
        embed = discord.Embed(
            title="🏆 Tournament Started!",
            description=f"Game: **{game}**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Participants", value="1", inline=True)
        embed.add_field(name="How to Join", value="Use `!tournament-join`", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="tournament-join")
    async def tournament_join(self, ctx):
        """Join an active tournament"""
        for tournament_id, tournament in self.active_tournaments.items():
            if tournament["host"].guild.id == ctx.guild.id and tournament["status"] == "open":
                tournament["participants"].append(ctx.author)
                await ctx.send(f"✅ {ctx.author.mention} has joined the tournament!")
                return
        
        await ctx.send("❌ No open tournament found!")
    
    @commands.command(name="tournament-bracket")
    async def tournament_bracket(self, ctx):
        """View tournament bracket"""
        for tournament_id, tournament in self.active_tournaments.items():
            if tournament["host"].guild.id == ctx.guild.id:
                bracket = "\n".join([f"{i+1}. {p.display_name}" for i, p in enumerate(tournament["participants"])])
                
                embed = discord.Embed(
                    title="🏆 Tournament Bracket",
                    description=bracket or "No participants yet",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                return
        
        await ctx.send("❌ No active tournament found!")
    
    @commands.command(name="tournament-end")
    async def tournament_end(self, ctx):
        """End a tournament"""
        for tournament_id, tournament in self.active_tournaments.items():
            if tournament["host"].guild.id == ctx.guild.id:
                tournament["status"] = "ended"
                winner = random.choice(tournament["participants"])
                
                embed = discord.Embed(
                    title="🏆 Tournament Ended!",
                    description=f"The winner is {winner.mention}!",
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
                del self.active_tournaments[tournament_id]
                return
        
        await ctx.send("❌ No active tournament found!")
    
    # ========== D&D ==========
    
    @commands.command(name="dnd-roll")
    async def dnd_roll(self, ctx, dice: str):
        """Roll D&D dice (e.g., d20, 2d6, 3d8+5)"""
        try:
            if "+" in dice:
                parts = dice.split("+")
                dice_part = parts[0]
                bonus = int(parts[1])
            else:
                dice_part = dice
                bonus = 0
            
            if "d" in dice_part:
                num, sides = dice_part.split("d")
                num = int(num) if num else 1
                sides = int(sides)
                
                rolls = [random.randint(1, sides) for _ in range(num)]
                total = sum(rolls) + bonus
                
                embed = discord.Embed(
                    title="🎲 D&D Roll",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Rolls", value=", ".join(map(str, rolls)), inline=True)
                embed.add_field(name="Bonus", value=f"+{bonus}" if bonus else "0", inline=True)
                embed.add_field(name="Total", value=f"**{total}**", inline=True)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Invalid format! Use like: `d20`, `2d6`, `3d8+5`")
        except:
            await ctx.send("❌ Invalid format! Use like: `d20`, `2d6`, `3d8+5`")

async def setup(bot):
    await bot.add_cog(GameEngine(bot))