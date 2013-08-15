import sys

from pyptlib.config import EnvError

SUPPORTED_TRANSPORT_VERSIONS = ['1']


class TransportPlugin(object):
    """
    Runtime process for a base TransportPlugin.

    Note: you cannot initialise this directly; either use
    ClientTransportPlugin() or ServerTransportPlugin().

    :var pyptlib.config.Config config: Configuration passed from Tor.
    :var file stdout: Output file descriptor to send status messages to.
    :var list served_transports: List of transports served by the plugin,
            populated by init().
    """
    def __init__(self, config=None, stdout=sys.stdout):
        self.config = config
        self.stdout = stdout
        self.served_transports = None # set by _declareSupports

    def init(self, supported_transports):
        """
        Initialise this transport plugin.

        If no explicit config was given, we read it from the standard TOR_PT_*
        environment variables.

        Then, we declare to Tor the transports that this plugin supports.

        After this is complete, you should initialise each transport method and
        call (this).reportMethodSuccess() or reportMethodError() as appropriate.
        When this is complete, you should then call reportMethodsEnd().

        :param list transports: List of transport methods this PT supports.

        :raises: :class:`pyptlib.config.EnvError` if environment was incomplete or corrupted.
                This also causes an ENV-ERROR line to be output, to inform Tor.
        """
        if not self.config:
            self.config = self._loadConfigFromEnv()
        self._declareSupports(supported_transports)

    def _loadConfigFromEnv(self):
        """
        Load the plugin config from the standard TOR_PT_* envvars.

        :raises: :class:`pyptlib.config.EnvError` if environment was incomplete or corrupted.
                This also causes an ENV-ERROR line to be output, to inform Tor.
        """
        try:
            return self.configType.fromEnv()
        except EnvError, e:
            print >>self.stdout, 'ENV-ERROR %s' % str(e)
            self.stdout.flush()
            raise e

    def _declareSupports(self, transports):
        """
        Declare to Tor the versions and transports that this PT supports.

        :returns: {"transports": wanted_transports} -- The subset of the
            declared inputs that were actually wanted by Tor.
        """
        versions = SUPPORTED_TRANSPORT_VERSIONS
        cfg = self.config

        wanted_versions = [v for v in versions if v in cfg.managedTransportVer]
        if not wanted_versions:
            self.emit('VERSION-ERROR no-version')
            raise EnvError("Unsupported managed proxy protocol version (%s)" %
                           cfg.managedTransportVer)
        else:
            self.emit('VERSION %s' % wanted_versions[0])

        if cfg.allTransportsEnabled:
            wanted_transports = transports.keys()
        else:
            # return able in priority-order determined by plugin
            wanted_transports = [t for t in transports if t in cfg.transports]

        self.served_transports = wanted_transports
        return { 'transports': wanted_transports }

    def reportMethodError(self, name, message):
        """
        Write a message to stdout announcing that we failed to launch a transport.

        :param str name: Name of transport.
        :param str message: Error message.
        """

        self.emit('%s-ERROR %s %s' % (self.methodName, name, message))

    def reportMethodsEnd(self):
        """
        Write a message to stdout announcing that we finished launching transports..
        """

        self.emit('%sS DONE' % self.methodName)

    def emit(self, msg):
        """
        Announce a message.

        :param str msg: A message.
        """

        print >>self.stdout, msg
        self.stdout.flush()

