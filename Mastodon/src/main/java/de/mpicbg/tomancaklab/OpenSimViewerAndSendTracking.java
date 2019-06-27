package de.mpicbg.tomancaklab;

import static org.mastodon.app.ui.ViewMenuBuilder.item;
import static org.mastodon.app.ui.ViewMenuBuilder.menu;

import org.mastodon.app.ui.ViewMenuBuilder;
import org.mastodon.plugin.MastodonPlugin;
import org.mastodon.plugin.MastodonPluginAppModel;

import org.mastodon.project.MamutProject;
import org.mastodon.revised.mamut.Mastodon;
import org.mastodon.revised.mamut.WindowManager;
import org.mastodon.spatial.SpatioTemporalIndex;
import org.mastodon.revised.mamut.MamutAppModel;
import org.mastodon.revised.model.mamut.Model;
import org.mastodon.revised.model.mamut.ModelGraph;
import org.mastodon.revised.model.mamut.Spot;
import org.mastodon.revised.model.mamut.Link;

import org.scijava.AbstractContextual;
import org.scijava.Context;
import org.scijava.plugin.Plugin;
import org.scijava.ui.behaviour.util.Actions;
import org.scijava.ui.behaviour.util.AbstractNamedAction;
import org.scijava.ui.behaviour.util.RunnableAction;
import org.scijava.log.LogService;

import javax.swing.*;
import java.io.File;
import java.util.*;

import org.zeromq.SocketType;
import org.zeromq.ZMQ;
import org.zeromq.ZMQException;


@Plugin( type = OpenSimViewerAndSendTracking.class )
public class OpenSimViewerAndSendTracking extends AbstractContextual implements MastodonPlugin
{
	//"IDs" of all plug-ins wrapped in this class
	private static final String PluginID_open = "LoPaT-OpenSimViewer";
	private static final String PluginID_send = "LoPaT-SendTracking";
	//------------------------------------------------------------------------

	@Override
	public List< ViewMenuBuilder.MenuItem > getMenuItems()
	{
		//this places the plug-in's menu items into the menu,
		//the titles of the items are defined right below
		return Arrays.asList(
				menu( "Plugins",
						item( PluginID_open ), item ( PluginID_send ) ) );
	}

	/** titles of this plug-in's menu items */
	private static Map< String, String > menuTexts = new HashMap<>();
	static
	{
		menuTexts.put( PluginID_open, "Open SimViewer" );
		menuTexts.put( PluginID_send, "Populate SimViewer" );
	}

	@Override
	public Map< String, String > getMenuTexts()
	{
		return menuTexts;
	}
	//------------------------------------------------------------------------

	private final AbstractNamedAction actionOpen;
	private final AbstractNamedAction actionSend;

	/** default c'tor: creates Actions available from this plug-in */
	public OpenSimViewerAndSendTracking()
	{
		actionOpen = new RunnableAction( PluginID_open, this::workerOpen );
		actionSend = new RunnableAction( PluginID_send, this::workerSend );
		updateEnabledActions();
	}

	/** register the actions to the application (with no shortcut keys) */
	@Override
	public void installGlobalActions( final Actions actions )
	{
		final String[] noShortCut = new String[] {};
		actions.namedAction( actionOpen, noShortCut );
		actions.namedAction( actionSend, noShortCut );
	}

	/** reference to the currently available project in Mastodon */
	private MastodonPluginAppModel pluginAppModel;

	/** learn about the current project's params */
	@Override
	public void setAppModel( final MastodonPluginAppModel model )
	{
		//the application reports back to us if some project is available
		this.pluginAppModel = model;
		updateEnabledActions();
	}

	/** enables/disables menu items based on the availability of some project */
	private void updateEnabledActions()
	{
		final MamutAppModel appModel = ( pluginAppModel == null ) ? null : pluginAppModel.getAppModel();
		actionOpen.setEnabled( appModel != null );
		actionSend.setEnabled( appModel != null );
	}
	//------------------------------------------------------------------------
	private LogService logServiceRef;
	private ZMQ.Socket socket = null;

	private String nodeMsg = new String();
	private int nodeMsgCnt = 0;

	private String lineMsg = new String();
	private int lineMsgCnt = 0;

	/** opens the SimViewer */
	private void workerOpen()
	{
		System.out.println("connecting to SimViewer");
		boolean connected = false;

		//init the communication side
		final ZMQ.Context zmqContext = ZMQ.context(1);
		try
		{
			socket = zmqContext.socket(SocketType.PAIR);
			if (socket == null)
				throw new Exception("Network sender: Cannot obtain local socket.");

			//port to listen for incoming data
			//socket.subscribe(new byte[] {});
			socket.connect("tcp://localhost:8765");
			connected = true;
		}
		catch (ZMQException e) {
			System.out.println("Network sender: Crashed with ZeroMQ error: " + e.getMessage());
		}
		catch (InterruptedException e) {
			System.out.println("Network sender: Interrupted.");
		}
		catch (Exception e) {
			System.out.println("Network sender: Error: " + e.getMessage());
			e.printStackTrace();
		}
		finally {
			if (socket != null && connected == false)
			{
				System.out.println("Network sender: Disconnecting...");
				socket.disconnect("tcp://localhost:8765");
				socket.close();
			}
			//zmqContext.close();
			//zmqContext.term();
		}

		if (connected) System.out.println("connected to SimViewer");
	}

	private void appendNodeToMsg(float[] pos, float radius, int color)
	{
		++nodeMsgCnt;
		nodeMsg = nodeMsg.concat( String.format(" %d %f %f %f %f %d",nodeMsgCnt,pos[0],pos[1],pos[2],radius,color) );
	}

	private void appendLineToMsg(float[] from, float[] to, int color)
	{
		++lineMsgCnt;
		lineMsg = lineMsg.concat( String.format(" %d %f %f %f %f %f %f %d",lineMsgCnt,from[0],from[1],from[2],to[0],to[1],to[2],color) );
	}

	private void sendAndClearAllMsgs()
	{
		if (socket != null)
		{
			if (nodeMsgCnt > 0)
				socket.send("v1 points "+nodeMsgCnt+" dim 3"+nodeMsg);

			if (lineMsgCnt > 0)
				socket.send("v1 lines "+lineMsgCnt+" dim 3"+lineMsg);

			socket.send("v1 tick Mastodon sent you "+nodeMsgCnt+" nodes with "+lineMsgCnt+" edges");
		}

		nodeMsg = new String();
		nodeMsgCnt = 0;
		lineMsg = new String();
		lineMsgCnt = 0;
	}


	/** sends some (now fake!) stuff to the SimViewer */
	private void workerSend()
	{
		final Model model = pluginAppModel.getAppModel().getModel();
		//final ModelGraph modelGraph = model.getGraph();
		final SpatioTemporalIndex< Spot > spots = model.getSpatioTemporalIndex();

		final int timeTill = pluginAppModel.getAppModel().getMaxTimepoint();
		for ( final Spot spot : spots.getSpatialIndex( timeTill ) )
		{
			float pos[] = new float[3];
			spot.localize(pos);
			appendNodeToMsg(pos,(float)Math.sqrt(spot.getBoundingSphereRadiusSquared()),2);
		}

		sendAndClearAllMsgs();
	}


	public static void main( final String[] args ) throws Exception
	{
		Locale.setDefault( Locale.US );
		UIManager.setLookAndFeel( UIManager.getSystemLookAndFeelClassName() );

		//final MamutProject project = new MamutProject( null, new File( "x=1000 y=1000 z=100 sx=1 sy=1 sz=10 t=400.dummy" ) );
		final MamutProject project = new MamutProject(
				new File( "/Users/ulman/DATA/CTC2/A_SomeTestingData/T_carto_9-3-15/2D/2D_mamut.mastodon" ),
				new File( "/Users/ulman/DATA/CTC2/A_SomeTestingData/T_carto_9-3-15/2D/dataset2.xml" ) );

		final Mastodon mastodon = new Mastodon();
		new Context().inject( mastodon );
		mastodon.run();
		mastodon.setExitOnClose();
		mastodon.openProject( project );
	}
}
