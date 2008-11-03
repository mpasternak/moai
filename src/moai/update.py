
from zope.interface import implements

from moai.interfaces import IDatabaseUpdater
from moai.error import ContentError, DatabaseError

class DatabaseUpdater(object):

    implements(IDatabaseUpdater)

    def __init__(self, content, content_class, database, log):
        self.set_database(database)
        self.set_content_provider(content)
        self.set_content_object_class(content_class)
        self.set_logger(log)

    def set_database(self, database):
        self.db = database

    def set_content_provider(self, content_provider):
        self._provider = content_provider

    def set_content_object_class(self, content_class):
        self._content_object_class = content_class

    def set_logger(self, log):
        self._log = log

    def update_provider(self, from_date=None):
        msg = 'Starting the update of %s' % self._provider.__class__.__name__
        if not from_date is None:
            msg += 'from %s' % from_date
        self._log.info(msg)
        count = 0
        for id in self._provider.update(from_date):
            yield id
            count += 1

        self._log.info('Updating %s returned %s new/modified objects' % (
            self._provider.__class__.__name__,
            count))
            

    def update_database(self, validate=True):    
        
        total = self._provider.count()
        self._log.info('Updating %s with %s %s objects' % (
            self.db.__class__.__name__,
            total,
            self._content_object_class.__name__))
        count = 0
        errors = 0
        for content_id in self._provider.get_content_ids():
            count += 1

            try:
                content_data = self._provider.get_content_by_id(content_id)
                content = self._content_object_class()
                content.update(content_data, self._provider)
            except Exception, err:
                errors += 1
                yield (count, total, content_id,
                       ContentError(self._content_object_class, content_id))
                continue
            
            if content.is_set:
                try:
                    self.db.add_set(content.id, content.label, content.get_values('description'))
                except Exception:
                    yield count, total, content.id, DatabaseError(content.id, 'set')
                    continue
                yield count, total, content.id, None
                continue
            
            id = content.id
            sets = content.sets
            record_data = {'id':content.id,
                           'content_type': content.content_type,
                           'when_modified': content.when_modified,
                           'deleted': content.deleted}

            metadata = {}
            got_error = False
            for name in content.field_names():
                try:
                    metadata[name] = content.get_values(name)
                except Exception:
                    yield count, total, content.id, DatabaseError(content.id, 'set')
                    got_error = True
                    break
            if got_error:
                continue

            assets = {}
            try:
                self.db.add_content(id, sets, record_data, metadata, assets)
            except Exception:
                yield count, total, content.id, DatabaseError(content.id, 'set')
                continue
            
            yield count, total, content.id, None