# ==========================================
# WEB LEADERBOARD (Fetches from Bot API)
# ==========================================

@app.route('/leaderboard/<server_id>')
def web_leaderboard(server_id):
    # Update this line with the new URL from your screenshot!
    bot_api_url = f"https://vodevsbot-production-820d.up.railway.app/api_leaderboard/{server_id}"
    
    try:
        response = requests.get(bot_api_url, timeout=10)
        if response.status_code != 200:
            return f"Failed to fetch leaderboard data from bot. Status: {response.status_code}", 500
        data = response.json()
    except Exception as e:
        return f"Error connecting to bot: {e}", 500
    
    if not data:
        return "No level data found.", 404
        
    formatted_users = []
    
    def format_xp(xp):
        if xp >= 1000000: return f"{xp/1000000:.1f}M"
        elif xp >= 1000: return f"{xp/1000:.1f}K"
        else: return str(xp)
            
    for user in data:
        user_id = user["user_id"]
        level = user["level"]
        xp = user["xp"]
        xp_formatted = format_xp(xp)
        
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_id}.png"
        
        formatted_users.append({
            "username": f"User {user_id[:4]}",
            "avatar_url": avatar_url,
            "level": level,
            "xp_formatted": xp_formatted
        })
        
    return render_template('leaderboard.html', server_name=f"Server {server_id[:4]}", users=formatted_users)
