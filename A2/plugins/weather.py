"""Functions related to weather."""
from typing import Optional, Union

from disco.bot import Plugin
from disco.bot.command import CommandEvent
from disco.types.message import MessageEmbed
from weather.weather import Weather, WeatherObject
from weather.objects.forecast_obj import Forecast
from weather.objects.unit_obj import Unit
from weather.objects.wind_obj import Wind


class WeatherPlugin(Plugin):
    CARDINAL_DIRS = (
        'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW',
        'WSW', 'W', 'WNW', 'NW', 'NNW')
    PRESSURE_STATES = ('steady', 'rising', 'falling')

    # Maps Yahoo's condition codes to OpenWeatherMap's weather icons and emojis.
    ICONS = (
        ('50d', '🌪️'), ('11d', '⛈️'), ('50d', '🌀'), ('11d', '⛈️'),
        ('11d', '🌩️'), ('13d', '🌨️'), ('13d', '🌨️'), ('13d', '🌨️'),
        ('09d', '💧'), ('09d', '💧'), ('09d', '🌧️'), ('09d', '🌧️'),
        ('09d', '🌧️'), ('13d', '🌨️'), ('13d', '🌨️'), ('13d', '🌨️'),
        ('13d', '🌨️'), ('09d', '🌧️'), ('13d', '🌨️'), ('50d', '💨'),
        ('50d', '🌫️'), ('50d', '🌫️'), ('50d', '💨'), ('50d', '💨'),
        ('50d', '💨'), ('13d', '❄️'), ('03d', '☁️'), ('02n', '☁️'),
        ('02d', '🌥️'), ('02n', '☁️'), ('02d', '⛅'), ('01n', '🌙'),
        ('01d', '☀️'), ('01n', '🌙'), ('01d', '🌤️'), ('09d', '🌧️'),
        ('01d', '♨️'), ('11d', '🌩️'), ('11d', '🌩️'), ('11d', '🌩️'),
        ('09d', '🌦️'), ('13d', '🌨️'), ('13d', '🌨️'), ('13d', '🌨️'),
        ('04d', '☁️'), ('11d', '🌩️'), ('13d', '🌨️'), ('11d', '🌩️'))

    def __init__(self, bot, config):
        super().__init__(bot, config)

        self.weather = Weather()

    @Plugin.command('weather', '<location:str...>')
    def weather_command(self, event: CommandEvent, location: str):
        """= weather =
        Displays the weather for a given location.
        Provides information on temperature, atmosphere, wind, & astronomy.
        usage    :: $weather <location>
        aliases  :: None
        category :: Weather
        == Arguments
        location :: The location for which to look up the weather.
        == Examples
        $weather new york `Looks up the weather for New York city.`
        $weather tokyo `Looks up the weather for Tokyo city.`
        """
        result: WeatherObject = self.weather.lookup_by_location(location)

        # Sometimes the response is OK but only contains units. Assumes failure
        # if some arbitrary top-level element besides units doesn't exist.
        if not result or 'link' not in result.print_obj:
            event.msg.reply('Could not find weather for `{}`.'.format(location))
            return

        embed: MessageEmbed = self.get_base_embed(result)
        embed.title = result.print_obj['item']['title']
        embed.set_thumbnail(url=self.get_thumbnail(result.condition.code))
        embed.description = self.format_condition(result)
        embed.add_field(
            name='Atmosphere',
            value=self.format_atmosphere(result.atmosphere, result.units),
            inline=True)
        embed.add_field(
            name='Wind',
            value=self.format_wind(result.wind, result.units),
            inline=True)
        embed.add_field(
            name='Astronomy',
            value=self.format_astronomy(result),
            inline=True)

        event.msg.reply(embed=embed)

    @Plugin.command('forecast', '<location:str...>')
    def forecast_command(self, event: CommandEvent, location: str):
        """= forecast =
        Displays a 10-day weather forecast for a given location.
        usage    :: $forecast <location>
        aliases  :: None
        category :: Weather
        == Arguments
        location :: The location for which to retrieve a forecast.
        == Examples
        $forecast new york `Looks up the forecast for New York city.`
        $forecast tokyo `Looks up the forecast for Tokyo city.`
        """
        result: WeatherObject = self.weather.lookup_by_location(location)

        # Sometimes the response is OK but only contains units. Assumes failure
        # if some arbitrary top-level element besides units doesn't exist.
        if not result or 'link' not in result.print_obj:
            event.msg.reply(
                'Could not retrieve a forecast for `{}`.'.format(location))
            return

        embed: MessageEmbed = self.get_base_embed(result)
        embed.title = '10-day Weather Forecast for {}'.format(result.title[17:])

        for forecast in result.forecast:
            emoji: str = WeatherPlugin.get_emoji(forecast.code)

            embed.add_field(
                name='{} ({})'.format(forecast.day, forecast.date[:6]),
                value='{}{}\nHigh: `{}° {}`\nLow: `{}° {}`'.format(
                    emoji, forecast.text, forecast.high,
                    result.units.temperature, forecast.low,
                    result.units.temperature),
                inline=True)

        event.msg.reply(embed=embed)

    @staticmethod
    def get_base_embed(result: WeatherObject) -> MessageEmbed:
        """Creates an embed and sets some common properties."""
        embed: MessageEmbed = MessageEmbed()
        embed.set_author(
            name='Yahoo! Weather',
            url='https://www.yahoo.com/news/weather',
            icon_url='https://s.yimg.com/dh/ap/default/130909/y_200_a.png')
        embed.url = result.print_obj['link'].split('*')[-1]  # Removes RSS URL.

        return embed

    @staticmethod
    def format_condition(result: WeatherObject) -> str:
        """Formats a string displaying the current condition information."""
        forecast: Forecast = result.forecast[0]
        emoji: str = WeatherPlugin.get_emoji(result.condition.code)

        return '{0}{1}° {5} - {2}\nHigh: `{3}° {5}`\nLow: `{4}° {5}`'.format(
            emoji, result.condition.temp, result.condition.text, forecast.high,
            forecast.low, result.units.temperature)

    @staticmethod
    def format_atmosphere(atm: dict, units: Unit) -> str:
        """Formats a string to displays atmosphere information."""
        state: str = WeatherPlugin.PRESSURE_STATES[int(atm['rising'])]

        return 'Humidity: `{}%`\nPressure: `{} {}` ({})\nVisibility: `{} {}`'\
            .format(atm["humidity"], atm["pressure"], units.pressure, state,
                    atm["visibility"], units.distance)

    @staticmethod
    def format_wind(wind: Wind, units: Unit) -> str:
        """Formats a string to displays wind information."""
        degrees: str = wind.direction
        cardinal: str = WeatherPlugin.get_cardinal_dir(degrees)

        return '`{}°` ({}) at `{} {}`\nWind chill: `{}`'.format(
            degrees, cardinal, wind.speed, units.speed, wind.chill)

    @staticmethod
    def format_astronomy(result: WeatherObject) -> str:
        """Formats a string to displays astronomy information."""
        tz: str = result.last_build_date[-3:]
        ast: dict = result.astronomy

        return 'Sunrise: `{0} {2}`\nSunset: `{1} {2}`'.format(
            ast["sunrise"], ast["sunset"], tz)

    @staticmethod
    def get_cardinal_dir(degrees: Union[int, str]) -> str:
        """Converts degrees to an abbreviated cardinal direction."""
        index: int = int((int(degrees) % 360 / 22.5) + 0.5)

        return WeatherPlugin.CARDINAL_DIRS[index]

    @staticmethod
    def get_emoji(code: Union[int, str]) -> str:
        """Returns an emoji based on a condition code."""
        code: int = int(code)

        return WeatherPlugin.ICONS[code][1] + ' ' if code != 3200 else ''

    @staticmethod
    def get_thumbnail(code: Union[int, str]) -> Optional[str]:
        """Returns an OpenWeatherMap icon URL based on a condition code."""
        code: int = int(code)

        if code != 3200:
            icon: str = WeatherPlugin.ICONS[code][0]

            return 'http://openweathermap.org/img/w/{}.png'.format(icon)
