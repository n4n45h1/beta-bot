const { Client, GatewayIntentBits, Partials, EmbedBuilder, MessageActionRow, MessageButton } = require('discord.js');
const express = require('express');
const passport = require('passport');
const DiscordStrategy = require('passport-discord').Strategy;
const session = require('express-session');
const axios = require('axios');
const dotenv = require('dotenv');

dotenv.config();

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent],
  partials: [Partials.Channel]
});

const app = express();

passport.serializeUser((user, done) => done(null, user));
passport.deserializeUser((obj, done) => done(null, obj));

passport.use(new DiscordStrategy({
  clientID: process.env.DISCORD_CLIENT_ID,
  clientSecret: process.env.DISCORD_CLIENT_SECRET,
  callbackURL: process.env.DISCORD_CALLBACK_URL,
  scope: ['identify', 'email']
}, (accessToken, refreshToken, profile, done) => {
  process.nextTick(() => done(null, profile));
}));

app.use(session({ secret: 'some secret', resave: false, saveUninitialized: false }));
app.use(passport.initialize());
app.use(passport.session());

app.get('/auth/discord', passport.authenticate('discord'));
app.get('/auth/discord/callback', passport.authenticate('discord', { failureRedirect: '/' }), (req, res) => {
  res.redirect('/info');
});

app.get('/info', isAuthenticated, async (req, res) => {
  const user = req.user;
  const ip = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
  
  let ipInfo = await axios.get(`https://ipinfo.io/${ip}?token=${process.env.IPINFO_TOKEN}`);
  ipInfo = ipInfo.data;

  if (await checkIfVPNOrProxy(ipInfo)) {
    sendDM(user, 'VPNまたはプロキシを使用しているため認証できません。');
    return res.send('VPNまたはプロキシを使用しているため認証できません。');
  }

  if (ipInfo.country !== 'JP') {
    const accountCreationDate = new Date(user.createdTimestamp);
    const now = new Date();
    const diffDays = Math.floor((now - accountCreationDate) / (1000 * 60 * 60 * 24));

    if (diffDays < 3) {
      sendDM(user, 'アカウントの作成日が3日以内のため認証できません。');
      return res.send('アカウントの作成日が3日以内のため認証できません。');
    }
  }

  const guild = client.guilds.cache.get(process.env.GUILD_ID);
  const member = await guild.members.fetch(user.id);
  const role = guild.roles.cache.find(role => role.name === process.env.ROLE_NAME);
  await member.roles.add(role);

  res.send('認証に成功しました。');
});

client.on('messageCreate', async message => {
  if (message.content.startsWith('.verify')) {
    const args = message.content.split(' ');
    const roleMention = args[1];

    const embed = new EmbedBuilder()
      .setTitle('認証')
      .setDescription('以下のボタンをクリックして認証を行ってください。')
      .setColor('#00FF00')
      .setTimestamp();

    message.channel.send({ embeds: [embed], components: [new MessageActionRow().addComponents(
      new MessageButton()
        .setCustomId('verify')
        .setLabel('認証')
        .setStyle('PRIMARY')
    )]});
  }

  if (message.content.startsWith('.log set')) {
    // ログチャネルの設定ロジック
  }

  if (message.content.startsWith('.log unset')) {
    // ログチャネルの削除ロジック
  }
});

client.on('interactionCreate', async interaction => {
  if (!interaction.isButton()) return;

  if (interaction.customId === 'verify') {
    await interaction.reply({ content: '認証を開始します。', ephemeral: true });
    interaction.followUp({ content: '[認証を行う](http://yourdomain.com/auth/discord)' });
  }
});

async function checkIfVPNOrProxy(ipInfo) {
  // IP情報を使ってVPNやプロキシかどうかをチェックするロジック
  return false; // 仮の実装
}

function sendDM(user, message) {
  client.users.cache.get(user.id).send(message);
}

function isAuthenticated(req, res, next) {
  if (req.isAuthenticated()) return next();
  res.redirect('/');
}

client.on('ready', () => {
  console.log(`Logged in as ${client.user.tag}`);
});

client.login(process.env.DISCORD_TOKEN);

app.listen(process.env.PORT || 3000, () => {
  console.log('Server is running...');
});
