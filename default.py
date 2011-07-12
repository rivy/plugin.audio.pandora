import xbmcgui
dlg = xbmcgui.DialogProgress()
dlg.create( "PANDORA", "Loading Script..." )
dlg.update( 0 )
import xbmc, os
import xbmcaddon

try:
	from libpandora.pandora import Pandora
except AttributeError, e:
	xbmcgui.Dialog().ok( "PANDORA", \
						 "ERROR: Something is wrong with your encryption keys." )
	raise e

from pandagui import PandaGUI
from pandaplayer import PandaPlayer

__title__ = "Pandora"
__settings__ = xbmcaddon.Addon(id='script.xbmc.pandora')

scriptPath = os.getcwd().replace(';','')

def GetGuiSetting( type, name ):
	resp = xbmc.executehttpapi( "GetGuiSetting( %d, %s )" %( type, name ) )
	resp = resp.replace( "<li>", "" )

	if type == 0:
		resp = int( resp )
	elif type == 1:
		resp = ( resp == "True" )
	elif type == 2:
		resp = float( resp )

	return resp

class PandaException( Exception ):
	pass

class Panda:

	def __init__( self ):
		self.gui = None
		self.pandora = None
		self.playlist = []
		self.curStation = ""
		self.playing = False
		self.skip = False
		self.die = False
		self.settings = __settings__
		
		fmt = self.settings.getSetting( "format" )
		self.pandora = Pandora( fmt )

		#Proxy settings
		if self.settings.getSetting( "proxy_enable" ):
			proxy_info = {
				"host" : self.settings.getSetting( "proxy_server" ),
				"port" : self.settings.getSetting( "proxy_port" ),
				"user" : self.settings.getSetting( "proxy_user" ),
				"pass" : self.settings.getsetting( "proxy_pass" )
			}
			self.pandora.setProxy( proxy_info )

		
		self.pandora.sync()
		
		while not self.auth():
			resp = xbmcgui.Dialog().yesno( "Pandora", \
					"Failed to authenticate listener.", \
					"Check username/password and try again.", \
					"Show Settings?" )
			if resp:
				self.settings.openSettings()
			else:
				self.quit()
				return

		self.player = PandaPlayer( panda = self )
		scriptSkinPath = os.path.join(scriptPath,"resources")
		self.gui = PandaGUI( "script-pandora.xml", scriptPath, \
							 "Default", "NTSC", panda = self )

	def auth( self ):
		user = self.settings.getSetting( "username" )
		pwd = self.settings.getSetting( "password" )
		if user == "" or pwd == "":
			return False
		dlg = xbmcgui.DialogProgress()
		dlg.create( "PANDORA", "Logging In..." )
		dlg.update( 0 )
		ret = self.pandora.authListener( user, pwd )
		dlg.close()
		return ret

	def playStation( self, stationId ):
		self.curStation = stationId
		self.playlist = []
		self.getMoreSongs()
		self.playing = True
		self.playNextSong()

	def getStations( self ):
		return self.pandora.getStations()
	
	def getMoreSongs( self ):
		if self.curStation == "":
			raise PandaException()
		items = []
		fragment = self.pandora.getFragment( self.curStation )
		for s in fragment:
			item = xbmcgui.ListItem( s["songTitle"] )
			item.setIconImage( s["artRadio"] )
			item.setThumbnailImage( s["artRadio"] )
			item.setProperty( "Cover", s["artRadio"] )
			info = { "title"	:	s["songTitle"], \
					 "artist"	:	s["artistSummary"], \
					 "album"	:	s["albumTitle"], \
					 "genre"	:	"".join(s["genre"]), \
					}
			item.setInfo( "music", info )
			items.append( ( s["audioURL"], item ) )
		self.playlist.extend( items )

	def playNextSong( self ):
		if not self.playing:
			raise PandaException()
		try:
			next = self.playlist.pop( 0 )
			self.player.playSong( next )
			art = next[1].getProperty( "Cover" )
			self.gui.setProperty( "AlbumArt", art )
		except IndexError:
			self.getMoreSongs()
		if len( self.playlist ) == 0:
			#Out of songs, grab some more while playing
			self.getMoreSongs()

	def skipSong( self ):
		self.skip = True
		self.player.stop()

	def main( self ):
		if self.die:
			return
		self.gui.doModal()
		self.cleanup()
		xbmc.sleep( 500 ) #Wait to make sure everything finishes

	def stop( self ):
		self.playing = False

	def cleanup( self ):
		self.skip = False
		if self.playing:
			self.playing = False
			self.player.stop()
		del self.gui
		del self.player

	def quit( self ):
		if self.gui != None:
			self.gui.close()

if __name__ == '__main__':
	if not ( os.path.exists( os.path.join( scriptPath, "crypt_key_input.h" ) ) \
			and os.path.exists( os.path.join( scriptPath, "crypt_key_output.h" ) ) ):
		xbmcgui.Dialog().ok( "Pandora", "Missing encription key files." )
		dlg.close()
	else:
		panda = Panda()
		panda.main()
		dlg.close()
